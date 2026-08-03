"""GET genérico com transporte injetável.

Generalização de ``audit/batching._get``. Deliberadamente NÃO consolida as
outras três cópias de urllib do projeto (``remote_ledger``, ``ollama_client``,
``leak_check``): ``batching.py`` não tem nenhum teste, e refatorar um caminho do
núcleo de auditoria sem rede de proteção — para viabilizar uma feature nova — é
a troca de risco errada. A dívida e a ordem correta estão em ADR-011.

``max_bytes`` é obrigatório, não opcional: um corpo truncado em silêncio
produziria o hash de um documento parcial, ou seja, uma mentira criptografada.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


class HttpError(RuntimeError):
    """Falha de transporte ou status inesperado."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class ResponseTooLarge(HttpError):
    """O corpo excedeu max_bytes. Nenhum hash é produzido."""


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes


class Transport(Protocol):
    """Injetável para que a suíte de testes rode inteiramente offline."""

    def request(self, url: str, *, headers: Mapping[str, str], timeout: int, max_bytes: int) -> HttpResponse: ...


class UrllibTransport:
    """Única implementação que toca a rede."""

    def request(self, url: str, *, headers: Mapping[str, str], timeout: int, max_bytes: int) -> HttpResponse:
        request = urllib.request.Request(url, headers=dict(headers))
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                # Lê um byte a mais para detectar estouro sem truncar em silêncio.
                body = response.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ResponseTooLarge(f"corpo excedeu {max_bytes} bytes: {url}", status=response.status)
                return HttpResponse(
                    url=url,
                    status=response.status,
                    headers={k.lower(): v for k, v in response.headers.items()},
                    body=body,
                )
        except urllib.error.HTTPError as error:
            detail = error.read(2048)
            return HttpResponse(
                url=url,
                status=error.code,
                headers={k.lower(): v for k, v in (error.headers or {}).items()},
                body=detail,
            )
        except (urllib.error.URLError, TimeoutError) as error:
            raise HttpError(f"inalcançável: {url} ({error})") from error


def get_bytes(
    url: str,
    *,
    headers: Mapping[str, str],
    timeout: int,
    max_bytes: int,
    transport: Transport | None = None,
) -> HttpResponse:
    """GET com limite de tamanho obrigatório."""
    if max_bytes <= 0:
        raise ValueError("max_bytes deve ser positivo")
    return (transport or UrllibTransport()).request(url, headers=headers, timeout=timeout, max_bytes=max_bytes)
