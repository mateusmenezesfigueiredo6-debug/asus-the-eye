from __future__ import annotations

import pytest

from asus_theye.markets.fonte_ptax import FontePTAXError, ptax_venda_fim_do_mes
from asus_theye.net.http import HttpResponse


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes = b"[]") -> None:
        self.status, self.body = status, body
        self.ultima_url = ""

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        self.ultima_url = url
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


def test_ptax_venda_fim_do_mes_pega_ultimo_ponto_do_mes() -> None:
    transporte = TransporteFalso(
        body=b'[{"data":"01/07/2026","valor":"5.30"},{"data":"29/07/2026","valor":"5.65"},{"data":"31/07/2026","valor":"5.55"}]'
    )

    assert ptax_venda_fim_do_mes("2026-07", transport=transporte) == pytest.approx(5.55)
    assert "dataInicial=01/07/2026" in transporte.ultima_url
    assert "dataFinal=31/07/2026" in transporte.ultima_url


def test_ptax_venda_fim_do_mes_mes_sem_publicacao_e_none() -> None:
    transporte = TransporteFalso(body=b"[]")

    assert ptax_venda_fim_do_mes("2026-08", transport=transporte) is None
    assert "dataInicial=01/08/2026" in transporte.ultima_url
    assert "dataFinal=31/08/2026" in transporte.ultima_url


@pytest.mark.parametrize(
    "mes,status,body",
    [
        ("2026-07", 500, b"erro"),
        ("2026-07", 200, b"nao-json"),
        ("2026-07", 200, b'{"nao":"lista"}'),
        ("2026-07", 200, b'[{"sem":"campos"}]'),
        ("2026-13", 200, b"[]"),
    ],
)
def test_ptax_venda_fim_do_mes_malformado_levanta(mes: str, status: int, body: bytes) -> None:
    with pytest.raises(FontePTAXError):
        ptax_venda_fim_do_mes(mes, transport=TransporteFalso(status=status, body=body))
