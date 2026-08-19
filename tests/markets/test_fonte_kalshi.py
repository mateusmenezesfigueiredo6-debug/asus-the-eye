"""Testes do conector do comparador (Kalshi) — offline, transporte falso."""

from __future__ import annotations

import pytest

from asus_theye.markets.fonte_kalshi import FonteKalshiError, preco_kalshi
from asus_theye.net.http import HttpResponse

CORPO = (
    b'{"market": {"ticker": "KXCPI-26AUG-T0.3", "title": "Will CPI rise more than 0.3%?",'
    b' "yes_bid_dollars": "0.5400", "yes_ask_dollars": "0.6900", "last_price_dollars": "0.5400",'
    b' "close_time": "2026-09-11T12:25:00Z", "status": "active"}}'
)


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes = CORPO) -> None:
        self.status, self.body = status, body

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


def test_preco_e_o_meio_do_spread_com_metodo_declarado() -> None:
    preco = preco_kalshi("KXCPI-26AUG-T0.3", transport=TransporteFalso())
    assert preco is not None
    assert preco.probabilidade_implicita == pytest.approx((0.54 + 0.69) / 2, abs=1e-6)
    assert "meio do spread" in preco.metodo_do_preco
    assert preco.status == "active" and preco.yes_bid == 0.54 and preco.yes_ask == 0.69


def test_sem_livro_cai_para_last_price() -> None:
    corpo = b'{"market": {"ticker": "T", "last_price_dollars": "0.3700", "status": "active"}}'
    preco = preco_kalshi("T", transport=TransporteFalso(body=corpo))
    assert preco is not None
    assert preco.probabilidade_implicita == pytest.approx(0.37, abs=1e-6)
    assert "last_price" in preco.metodo_do_preco


def test_mercado_inexistente_e_none() -> None:
    assert preco_kalshi("NAO-EXISTE", transport=TransporteFalso(status=404, body=b"{}")) is None


@pytest.mark.parametrize(
    "status,body",
    [
        (500, b"{}"),
        (200, b"nao-e-json"),
        (200, b'{"sem_market": 1}'),
        (200, b'{"market": {"ticker": "T", "yes_bid_dollars": "abc", "yes_ask_dollars": "0.5"}}'),
        (200, b'{"market": {"ticker": "T", "yes_bid_dollars": "54", "yes_ask_dollars": "0.5"}}'),
        (200, b'{"market": {"ticker": "T", "status": "active"}}'),
    ],
)
def test_malformado_ou_sem_preco_levanta(status: int, body: bytes) -> None:
    with pytest.raises(FonteKalshiError):
        preco_kalshi("T", transport=TransporteFalso(status=status, body=body))
