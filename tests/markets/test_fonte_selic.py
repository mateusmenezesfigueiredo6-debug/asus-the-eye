# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import pytest

from asus_theye.markets.fonte_selic import FonteSelicError, selic_meta
from asus_theye.net.http import HttpResponse


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes = b"[]") -> None:
        self.status, self.body = status, body
        self.urls: list[str] = []

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        self.urls.append(url)
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


CORPO = b'[{"data":"01/07/2026","valor":"14.75"},{"data":"31/07/2026","valor":"15.00"}]'


def test_selic_meta_acha_o_ultimo_ponto_do_mes() -> None:
    transporte = TransporteFalso(body=CORPO)
    assert selic_meta("2026-07", transport=transporte) == pytest.approx(15.0)
    assert transporte.urls == [
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
        "?formato=json&dataInicial=01/07/2026&dataFinal=31/07/2026"
    ]


def test_selic_meta_mes_sem_valor_publicado_e_none() -> None:
    assert selic_meta("2026-08", transport=TransporteFalso(body=b"[]")) is None


@pytest.mark.parametrize(
    "status,body",
    [(500, b"erro"), (200, b"nao-json"), (200, b'{"nao":"lista"}'), (200, b'[{"sem":"campos"}]')],
)
def test_selic_meta_resposta_invalida_levanta(status: int, body: bytes) -> None:
    with pytest.raises(FonteSelicError):
        selic_meta("2026-07", transport=TransporteFalso(status=status, body=body))
