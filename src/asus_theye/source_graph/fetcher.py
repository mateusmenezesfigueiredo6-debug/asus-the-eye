# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fetcher educado: robots, rate limit, backoff, limite de tamanho, licença.

Duas exceções com significados diferentes, porque tratá-las igual seria um bug:

- :class:`FetchRefusal` — recusa deliberada (robots proíbe, corpo grande demais,
  licença ausente). **Nunca deve ser reintentada**: repetir uma recusa é insistir
  contra uma regra.
- :class:`FetchError` — falha de transporte ou 5xx. Pode ser reintentada dentro
  da política.

``clock``, ``sleeper`` e ``transport`` são injetados, então a suíte inteira roda
offline, instantânea e determinística — nenhum teste toca a rede.
"""

from __future__ import annotations

import hashlib
import random
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

from asus_theye.net.http import HttpError, HttpResponse, ResponseTooLarge, Transport, get_bytes
from asus_theye.source_graph.robots import RobotsCache

DEFAULT_MIN_INTERVAL_SECONDS = 3.0  # limite do arXiv: errar para o lado educado
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_BACKOFF_SECONDS = 60.0


class FetchRefusal(RuntimeError):
    """Recusa deliberada. NUNCA reintentar."""


class FetchError(RuntimeError):
    """Falha reintentável dentro da política."""


@dataclass(frozen=True)
class FetchPolicy:
    user_agent: str
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS
    max_bytes: int = 5_242_880
    max_retries: int = 3
    timeout_seconds: int = 30
    access_basis: str = "robots"
    """'robots' | 'api_terms:<terms_url>'. A base fica gravada em cada resultado."""

    def __post_init__(self) -> None:
        if not self.user_agent or "(" not in self.user_agent:
            raise ValueError("user_agent deve identificar o cliente e um contato")
        if self.min_interval_seconds <= 0:
            raise ValueError("min_interval_seconds deve ser positivo")
        if self.max_bytes <= 0:
            raise ValueError("max_bytes deve ser positivo")


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    retrieved_at: str
    content_hash_sha256: str
    content_type: str
    byte_length: int
    body: bytes
    license_id: str
    robots_decision: str
    connector_id: str
    retries: int
    waited_seconds: float


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class PoliteFetcher:
    """Um fetcher por conector; o rate limit é por host."""

    policy: FetchPolicy
    connector_id: str
    license_id: str
    transport: Transport | None = None
    clock: Callable[[], float] = time.monotonic
    sleeper: Callable[[float], None] = time.sleep
    jitter: Callable[[], float] = random.random
    robots: RobotsCache | None = None
    _last_request_at: dict[str, float] = field(default_factory=dict)
    # Protege o par (ler _last_request_at, decidir, gravar) sob concorrência.
    # O sono acontece FORA do lock (senão um host lento serializaria os outros);
    # por isso _wait_for_slot reconfere o slot depois de dormir.
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if not self.license_id:
            raise FetchRefusal(
                f"{self.connector_id}: sem license_id declarado em connectors.json — licença nunca é deduzida de página"
            )
        if self.robots is None:
            self.robots = RobotsCache(fetch_text=self._fetch_robots_text, clock=self.clock)

    # ----------------------------------------------------------------- robots

    def _fetch_robots_text(self, robots_url: str) -> str | None:
        try:
            response = get_bytes(
                robots_url,
                headers={"user-agent": self.policy.user_agent},
                timeout=self.policy.timeout_seconds,
                max_bytes=self.policy.max_bytes,
                transport=self.transport,
            )
        except HttpError:
            return None
        if response.status != 200:
            return None
        return response.body.decode("utf-8", errors="replace")

    def allowed(self, url: str) -> tuple[bool, str]:
        """(permitido, base da decisão) — a base fica registrada, nunca implícita."""
        if self.policy.access_basis.startswith("api_terms:"):
            return True, self.policy.access_basis
        assert self.robots is not None
        return self.robots.allowed(url, self.policy.user_agent)

    # ------------------------------------------------------------- rate limit

    def _wait_for_slot(self, url: str) -> float:
        host = urlsplit(url).netloc
        waited = 0.0
        while True:
            with self._lock:
                now = self.clock()
                last = self._last_request_at.get(host)
                if last is None or now - last >= self.policy.min_interval_seconds:
                    self._last_request_at[host] = self.clock()
                    return waited
                falta = self.policy.min_interval_seconds - (now - last)
            # dorme FORA do lock e reconfere: outra thread pode ter tomado o slot
            self.sleeper(falta)
            waited += falta

    def _backoff(self, attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                return float(retry_after)  # Retry-After honrado, vence o cálculo
            except ValueError:
                pass
        return min(2.0**attempt, MAX_BACKOFF_SECONDS) * self.jitter()

    # ------------------------------------------------------------------ fetch

    def get(self, url: str) -> FetchResult:
        permitted, decision = self.allowed(url)
        if not permitted:
            raise FetchRefusal(f"{decision}: {url}")

        waited_total = 0.0
        headers: Mapping[str, str] = {
            "user-agent": self.policy.user_agent,
            "accept": "application/json, text/plain, */*",
        }

        for attempt in range(self.policy.max_retries + 1):
            waited_total += self._wait_for_slot(url)
            try:
                response = get_bytes(
                    url,
                    headers=headers,
                    timeout=self.policy.timeout_seconds,
                    max_bytes=self.policy.max_bytes,
                    transport=self.transport,
                )
            except ResponseTooLarge as error:
                # Nenhum hash é produzido: hash de documento truncado é mentira.
                raise FetchRefusal(str(error)) from error
            except HttpError as error:
                if attempt >= self.policy.max_retries:
                    raise FetchError(str(error)) from error
                pause = self._backoff(attempt, None)
                self.sleeper(pause)
                waited_total += pause
                continue

            if response.status in RETRYABLE_STATUS:
                if attempt >= self.policy.max_retries:
                    raise FetchError(f"HTTP {response.status} após {attempt + 1} tentativas: {url}")
                pause = self._backoff(attempt, response.headers.get("retry-after"))
                self.sleeper(pause)
                waited_total += pause
                continue

            if response.status >= 400:
                # 403/404 são respostas, não falhas: nunca reintentadas.
                raise FetchRefusal(f"HTTP {response.status}: {url}")

            return self._to_result(response, decision, attempt, waited_total)

        raise FetchError(f"tentativas esgotadas: {url}")  # pragma: no cover

    def _to_result(self, response: HttpResponse, decision: str, retries: int, waited: float) -> FetchResult:
        return FetchResult(
            url=response.url,
            status=response.status,
            retrieved_at=_utc_now(),
            content_hash_sha256=hashlib.sha256(response.body).hexdigest(),
            content_type=response.headers.get("content-type", ""),
            byte_length=len(response.body),
            body=response.body,
            license_id=self.license_id,
            robots_decision=decision,
            connector_id=self.connector_id,
            retries=retries,
            waited_seconds=round(waited, 3),
        )
