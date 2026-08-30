# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector ANEEL — bandeira tarifária.

O risco específico desta fonte é a tradução de CATEGORIA para NÚMERO. Uma
escada aberta, que devolvesse 0 para rótulo desconhecido, faria uma bandeira
nova (ou renomeada) liquidar como se fosse verde — o desfecho mais barato,
justamente no mês em que a conta subiu.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.fonte_aneel import FonteAneelError, nivel_da_bandeira
from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpResponse

CABECALHO = '"DatGeracaoConjuntoDados";"DatCompetencia";"NomBandeiraAcionada";"VlrAdicionalBandeira"'


def csv_com(*linhas: str) -> bytes:
    return ("\n".join([CABECALHO, *linhas])).encode("utf-8")


PADRAO = csv_com(
    '"2026-08-24";"2026-06-01";"Verde";",00"',
    '"2026-08-24";"2026-07-01";"Amarela";"18,85"',
    '"2026-08-24";"2026-08-01";"Vermelha P2";"79,71"',
)


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.status, self.body = status, PADRAO if body is None else body

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


@pytest.mark.parametrize("mes,nivel", [("2026-06", 0.0), ("2026-07", 1.0), ("2026-08", 3.0)])
def test_traduz_a_bandeira_para_a_escada(mes: str, nivel: float) -> None:
    assert nivel_da_bandeira(mes, transport=TransporteFalso()) == pytest.approx(nivel)


def test_competencia_nao_acionada_e_none() -> None:
    """Mês futuro não está no CSV. É UNKNOWN, jamais 'verde'."""
    assert nivel_da_bandeira("2026-12", transport=TransporteFalso()) is None


def test_bandeira_desconhecida_levanta_nunca_vira_verde() -> None:
    """O teste mais importante do módulo.

    Uma escada aberta devolveria 0 (verde, sem cobrança) para um rótulo novo —
    o desfecho mais barato, exatamente no mês em que a conta subiu.
    """
    nova = csv_com('"2026-08-24";"2026-09-01";"Vermelha P3";"120,00"')
    with pytest.raises(FonteAneelError, match="não está na escada"):
        nivel_da_bandeira("2026-09", transport=TransporteFalso(body=nova))


def test_acento_e_caixa_do_rotulo_nao_quebram() -> None:
    escassez = csv_com('"2026-08-24";"2026-09-01";"ESCASSEZ HÍDRICA";"142,00"')
    assert nivel_da_bandeira("2026-09", transport=TransporteFalso(body=escassez)) == pytest.approx(4.0)


def test_competencia_duplicada_levanta() -> None:
    dupla = csv_com(
        '"2026-08-24";"2026-07-01";"Amarela";"18,85"',
        '"2026-08-24";"2026-07-01";"Verde";",00"',
    )
    with pytest.raises(FonteAneelError, match="2 vezes"):
        nivel_da_bandeira("2026-07", transport=TransporteFalso(body=dupla))


def test_layout_do_csv_mudou_levanta() -> None:
    outro = b'"Mes";"Bandeira"\n"2026-07";"Amarela"'
    with pytest.raises(FonteAneelError, match="layout mudou"):
        nivel_da_bandeira("2026-07", transport=TransporteFalso(body=outro))


@pytest.mark.parametrize("mes", ["2026-13", "2026", "07/2026", "2026-1"])
def test_mes_malformado_levanta(mes: str) -> None:
    with pytest.raises(FonteAneelError, match="formato inesperado"):
        nivel_da_bandeira(mes, transport=TransporteFalso())


@pytest.mark.parametrize("status,body", [(500, b"erro"), (404, b"x"), (200, b""), (200, CABECALHO.encode())])
def test_resposta_invalida_levanta(status: int, body: bytes) -> None:
    with pytest.raises(FonteAneelError):
        nivel_da_bandeira("2026-07", transport=TransporteFalso(status=status, body=body))


def test_erro_da_aneel_e_capturavel_pela_raiz_comum() -> None:
    with pytest.raises(FonteError):
        nivel_da_bandeira("2026-07", transport=TransporteFalso(status=500))
