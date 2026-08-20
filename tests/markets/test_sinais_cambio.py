# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes de sinais_cambio — offline, com transporte injetado."""

from __future__ import annotations

import pytest

from asus_theye.markets.sinais_cambio import (
    PESO_FOCUS,
    PESO_PTAX,
    SinaisCambioError,
    mediana_focus_cambio,
    probabilidade_para_cambio,
    sinais_para_cambio,
)
from asus_theye.net.http import HttpError, HttpResponse

OLINDA_COM_MEDIANA = b'{"value":[{"Data":"2026-08-14","Mediana":5.25}]}'
OLINDA_VAZIO = b'{"value":[]}'
SGS_COM_PTAX = b'[{"data":"30/09/2026","valor":"5.2800"}]'
# Empty array = BCB ainda não publicou o mês (UNKNOWN over guess → None)
SGS_VAZIO = b"[]"


class TransporteRoteado:
    def __init__(self, olinda: tuple[int, bytes], sgs: tuple[int, bytes]) -> None:
        self.olinda, self.sgs = olinda, sgs

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        status, body = self.olinda if "olinda.bcb.gov.br" in url else self.sgs
        return HttpResponse(url=url, status=status, headers={}, body=body)


# --------------------------------------------------------------- Focus/Olinda


def test_mediana_focus_acha_a_linha() -> None:
    t = TransporteRoteado((200, OLINDA_COM_MEDIANA), (200, SGS_VAZIO))
    assert mediana_focus_cambio("2026-09", transport=t) == (5.25, "2026-08-14")


def test_mediana_focus_mes_sem_linha_e_none() -> None:
    t = TransporteRoteado((200, OLINDA_VAZIO), (200, SGS_VAZIO))
    assert mediana_focus_cambio("2026-09", transport=t) is None


@pytest.mark.parametrize("status,body", [(500, b"{}"), (200, b"nao-e-json"), (200, b'{"sem_value": 1}')])
def test_mediana_focus_malformado_levanta(status: int, body: bytes) -> None:
    t = TransporteRoteado((status, body), (200, SGS_VAZIO))
    with pytest.raises(SinaisCambioError):
        mediana_focus_cambio("2026-09", transport=t)


def test_mes_referencia_invalido_levanta() -> None:
    with pytest.raises(SinaisCambioError, match="aaaa-mm"):
        mediana_focus_cambio("09/2026", transport=TransporteRoteado((200, OLINDA_VAZIO), (200, SGS_VAZIO)))


def test_fonte_inalcancavel_levanta() -> None:
    class TFalso:
        def request(self, url: str, **_: object) -> object:
            raise HttpError("timeout")

    with pytest.raises(SinaisCambioError, match="inalcançável"):
        mediana_focus_cambio("2026-09", transport=TFalso())  # type: ignore[arg-type]


# --------------------------------------------------------------- sinais


def test_sinais_direcao_e_peso_declarados() -> None:
    # Focus 5.25 >= 5.00 → SIM peso 20; PTAX 5.28 >= 5.00 → SIM peso 10
    t = TransporteRoteado((200, OLINDA_COM_MEDIANA), (200, SGS_COM_PTAX))
    sinais = sinais_para_cambio("2026-09", 5.00, transport=t)
    assert [(s.direcao, s.peso) for s in sinais] == [("sim", PESO_FOCUS), ("sim", PESO_PTAX)]
    assert all(s.fonte for s in sinais)
    assert "Focus" in sinais[0].fonte and "SGS 1" in sinais[1].fonte


def test_sinais_direcao_nao_quando_abaixo_do_limiar() -> None:
    # Focus 5.25 < 5.50 → NÃO; PTAX sem o mês → ausente
    t = TransporteRoteado((200, OLINDA_COM_MEDIANA), (200, SGS_VAZIO))
    sinais = sinais_para_cambio("2026-09", 5.50, transport=t)
    assert len(sinais) == 1
    assert sinais[0].direcao == "nao" and sinais[0].peso == PESO_FOCUS


def test_sem_nenhuma_fonte_probabilidade_e_o_prior_honesto() -> None:
    t = TransporteRoteado((200, OLINDA_VAZIO), (200, SGS_VAZIO))
    prob = probabilidade_para_cambio("2026-09", 5.00, transport=t)
    assert prob.valor == 0.5 and prob.max_uncertainty is True and prob.fontes == []


def test_probabilidade_so_com_focus_sim() -> None:
    t = TransporteRoteado((200, OLINDA_COM_MEDIANA), (200, SGS_VAZIO))
    prob = probabilidade_para_cambio("2026-09", 5.00, transport=t)
    # WPAM: (0.5*10 + 20) / (10 + 20 + 0) = 25/30
    assert prob.valor == pytest.approx(25 / 30, abs=1e-6)
    assert prob.max_uncertainty is False
