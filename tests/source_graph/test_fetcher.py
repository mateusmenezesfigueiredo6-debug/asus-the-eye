"""Testes do fetcher educado. Transporte, relógio e sleeper falsos: ZERO rede."""

from __future__ import annotations

import hashlib

import pytest

from asus_theye.net.http import HttpError, HttpResponse, ResponseTooLarge
from asus_theye.source_graph.fetcher import (
    FetchError,
    FetchPolicy,
    FetchRefusal,
    PoliteFetcher,
)

UA = "asus-theye-source-graph/0.1 (+contato@exemplo.invalid)"


class FakeTransport:
    """Registra cada chamada e devolve respostas roteirizadas."""

    def __init__(self, routes: dict[str, list[HttpResponse | Exception]]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def request(self, url, *, headers, timeout, max_bytes):
        self.calls.append(url)
        queue = self.routes.get(url)
        if not queue:
            return HttpResponse(url=url, status=404, headers={}, body=b"")
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class FakeSleeper:
    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.slept: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.clock.now += seconds


def ok(url: str, body: bytes = b'{"ok":true}') -> HttpResponse:
    return HttpResponse(url=url, status=200, headers={"content-type": "application/json"}, body=body)


def build(routes: dict, *, policy: FetchPolicy | None = None):
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    transport = FakeTransport(routes)
    fetcher = PoliteFetcher(
        policy=policy or FetchPolicy(user_agent=UA),
        connector_id="fake",
        license_id="CC0-1.0",
        transport=transport,
        clock=clock,
        sleeper=sleeper,
        jitter=lambda: 1.0,
    )
    return fetcher, transport, sleeper, clock


# --------------------------------------------------------------------- robots


def test_robots_disallow_blocks_and_no_content_request_is_made() -> None:
    url = "https://example.invalid/data"
    fetcher, transport, _, _ = build(
        {
            "https://example.invalid/robots.txt": [
                HttpResponse(
                    url="https://example.invalid/robots.txt",
                    status=200,
                    headers={},
                    body=b"User-agent: *\nDisallow: /\n",
                )
            ],
            url: [ok(url)],
        }
    )
    with pytest.raises(FetchRefusal, match="robots_disallowed"):
        fetcher.get(url)
    assert url not in transport.calls, "nenhuma requisição de conteúdo pode ter sido emitida"


def test_missing_robots_file_is_allowed_with_named_reason() -> None:
    url = "https://example.invalid/data"
    fetcher, _, _, _ = build(
        {
            "https://example.invalid/robots.txt": [HttpResponse(url="", status=404, headers={}, body=b"")],
            url: [ok(url)],
        }
    )
    result = fetcher.get(url)
    assert result.robots_decision == "no_robots_file"


def test_api_terms_basis_is_recorded_not_silent() -> None:
    """Termos de API que autorizam uso programático: a base fica gravada."""
    url = "https://api.invalid/works"
    policy = FetchPolicy(user_agent=UA, access_basis="api_terms:https://api.invalid/terms")
    fetcher, transport, _, _ = build({url: [ok(url)]}, policy=policy)
    result = fetcher.get(url)
    assert result.robots_decision == "api_terms:https://api.invalid/terms"
    assert not any("robots.txt" in call for call in transport.calls)


# ----------------------------------------------------------------- rate limit


def test_minimum_interval_is_respected_between_requests() -> None:
    url = "https://example.invalid/a"
    fetcher, _, sleeper, _ = build(
        {
            "https://example.invalid/robots.txt": [HttpResponse(url="", status=404, headers={}, body=b"")],
            url: [ok(url)],
        }
    )
    fetcher.get(url)
    fetcher.get(url)
    assert any(s >= 3.0 for s in sleeper.slept), f"esperava espera >= 3 s, veio {sleeper.slept}"


# --------------------------------------------------------------------- limite


def test_body_over_max_bytes_refuses_and_produces_no_hash() -> None:
    url = "https://example.invalid/big"
    fetcher, _, _, _ = build(
        {
            "https://example.invalid/robots.txt": [HttpResponse(url="", status=404, headers={}, body=b"")],
            url: [ResponseTooLarge("corpo excedeu 10 bytes")],
        }
    )
    with pytest.raises(FetchRefusal, match="excedeu"):
        fetcher.get(url)


# --------------------------------------------------------------------- retry


def test_429_honours_retry_after_then_succeeds() -> None:
    url = "https://example.invalid/limited"
    fetcher, _, sleeper, _ = build(
        {
            "https://example.invalid/robots.txt": [HttpResponse(url="", status=404, headers={}, body=b"")],
            url: [
                HttpResponse(url=url, status=429, headers={"retry-after": "2"}, body=b""),
                ok(url),
            ],
        }
    )
    result = fetcher.get(url)
    assert result.status == 200
    assert 2.0 in sleeper.slept, f"Retry-After deve vencer o backoff: {sleeper.slept}"
    assert result.retries == 1


def test_403_is_never_retried() -> None:
    url = "https://example.invalid/forbidden"
    fetcher, transport, _, _ = build(
        {
            "https://example.invalid/robots.txt": [HttpResponse(url="", status=404, headers={}, body=b"")],
            url: [HttpResponse(url=url, status=403, headers={}, body=b"")],
        }
    )
    with pytest.raises(FetchRefusal, match="403"):
        fetcher.get(url)
    assert transport.calls.count(url) == 1, "403 é resposta, não falha: zero retentativas"


def test_500_retries_then_raises_fetch_error() -> None:
    url = "https://example.invalid/broken"
    policy = FetchPolicy(user_agent=UA, max_retries=2)
    fetcher, transport, _, _ = build(
        {
            "https://example.invalid/robots.txt": [HttpResponse(url="", status=404, headers={}, body=b"")],
            url: [HttpResponse(url=url, status=500, headers={}, body=b"")],
        },
        policy=policy,
    )
    with pytest.raises(FetchError, match="500"):
        fetcher.get(url)
    assert transport.calls.count(url) == 3, "1 tentativa + 2 retentativas"


def test_transport_failure_is_retryable() -> None:
    url = "https://example.invalid/flaky"
    policy = FetchPolicy(user_agent=UA, max_retries=1)
    fetcher, _, _, _ = build(
        {
            "https://example.invalid/robots.txt": [HttpResponse(url="", status=404, headers={}, body=b"")],
            url: [HttpError("inalcançável")],
        },
        policy=policy,
    )
    with pytest.raises(FetchError, match="inalcançável"):
        fetcher.get(url)


# ------------------------------------------------------------------ resultado


def test_hash_is_of_the_exact_bytes_received() -> None:
    url = "https://example.invalid/doc"
    payload = b'{"titulo":"exemplo"}'
    fetcher, _, _, _ = build(
        {
            "https://example.invalid/robots.txt": [HttpResponse(url="", status=404, headers={}, body=b"")],
            url: [ok(url, payload)],
        }
    )
    result = fetcher.get(url)
    assert result.content_hash_sha256 == hashlib.sha256(payload).hexdigest()
    assert result.byte_length == len(payload)
    assert result.license_id == "CC0-1.0"
    assert result.connector_id == "fake"


def test_user_agent_must_identify_a_contact() -> None:
    with pytest.raises(ValueError, match="contato"):
        FetchPolicy(user_agent="python-urllib/3.12")


def test_connector_without_license_is_refused() -> None:
    """Licença nunca é deduzida de página: sem license_id, o fetcher recusa nascer."""
    with pytest.raises(FetchRefusal, match="license_id"):
        PoliteFetcher(policy=FetchPolicy(user_agent=UA), connector_id="sem-licenca", license_id="")


def test_there_is_no_way_to_disable_robots() -> None:
    """A checagem não é um parâmetro: nenhum campo da política a desliga."""
    assert not any(
        "robots" in field_name and "disable" in field_name.lower() for field_name in FetchPolicy.__dataclass_fields__
    )
    assert "respect_robots" not in FetchPolicy.__dataclass_fields__
