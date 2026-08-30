# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector Loterias Caixa — Mega-Sena.

A armadilha específica desta fonte: a API é indexada por CONCURSO e o contrato
é indexado por DIA. Ler o concurso corrente e usar o número sem conferir a data
liquidaria o mercado de sábado com o resultado de quarta — e o resultado
estaria certo, só que do sorteio errado. É isso que a maior parte destes testes
protege.
"""

from __future__ import annotations

import json

import pytest

from asus_theye.markets.fonte_base import FonteError
from asus_theye.markets.fonte_caixa import (
    FonteCaixaError,
    dezenas_pares,
    ganhadores_da_quina,
    soma_das_dezenas,
)
from asus_theye.net.http import HttpResponse

#: Concurso 3050, apurado em 27/08/2026 — resposta real da Caixa, lida ao vivo.
#: Dezenas 11,14,30,38,49,55: soma 197, 3 pares, 26 apostas na quina.
def corpo(**sobrescreve: object) -> bytes:
    dados: dict = {
        "numero": 3050,
        "dataApuracao": "27/08/2026",
        "acumulado": True,
        "listaDezenas": ["11", "14", "30", "38", "49", "55"],
        "listaRateioPremio": [
            {"descricaoFaixa": "6 acertos", "numeroDeGanhadores": 0},
            {"descricaoFaixa": "5 acertos", "numeroDeGanhadores": 26},
            {"descricaoFaixa": "4 acertos", "numeroDeGanhadores": 1682},
        ],
    }
    dados.update(sobrescreve)
    return json.dumps(dados).encode("utf-8")


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.status, self.body = status, body if body is not None else corpo()

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


DIA = "2026-08-27"


def test_le_as_tres_medidas_do_concurso_do_dia() -> None:
    assert soma_das_dezenas(DIA, transport=TransporteFalso()) == pytest.approx(197.0)
    assert dezenas_pares(DIA, transport=TransporteFalso()) == pytest.approx(3.0)
    assert ganhadores_da_quina(DIA, transport=TransporteFalso()) == pytest.approx(26.0)


def test_dia_sem_sorteio_e_none_nunca_o_concurso_anterior() -> None:
    """A guarda central: o concurso corrente é de OUTRO dia.

    Sem isso, o mercado de sábado liquidaria com o resultado de quarta — um
    número verdadeiro, do sorteio errado.
    """
    for fetcher in (soma_das_dezenas, dezenas_pares, ganhadores_da_quina):
        assert fetcher("2026-08-28", transport=TransporteFalso()) is None


@pytest.mark.parametrize("dia", ["2026-8-27", "27/08/2026", "2026-08-32", "2026-13-01", "2026-08"])
def test_dia_malformado_e_recusado(dia: str) -> None:
    with pytest.raises(FonteCaixaError, match="formato inesperado"):
        soma_das_dezenas(dia, transport=TransporteFalso())


@pytest.mark.parametrize(
    "dezenas",
    [
        ["11", "14", "30", "38", "49"],          # só 5
        ["11", "14", "30", "38", "49", "55", "60"],  # 7
        ["11", "14", "30", "38", "49", "61"],    # fora do volante
        ["11", "14", "30", "38", "49", "0"],     # fora do volante
        ["11", "11", "30", "38", "49", "55"],    # repetida
        ["11", "14", "30", "38", "49", "abc"],   # não numérica
    ],
)
def test_resultado_impossivel_levanta(dezenas: list[str]) -> None:
    with pytest.raises(FonteCaixaError):
        soma_das_dezenas(DIA, transport=TransporteFalso(body=corpo(listaDezenas=dezenas)))


def test_faixa_da_quina_renomeada_levanta() -> None:
    """Se a Caixa mudar o rótulo, é melhor parar do que devolver a faixa errada."""
    outras = [{"descricaoFaixa": "Sena", "numeroDeGanhadores": 0}]
    with pytest.raises(FonteCaixaError, match="mudou os rótulos"):
        ganhadores_da_quina(DIA, transport=TransporteFalso(body=corpo(listaRateioPremio=outras)))


@pytest.mark.parametrize("ganhadores", [None, "26", -1, True, 3.5])
def test_numero_de_ganhadores_invalido_levanta(ganhadores: object) -> None:
    faixas = [{"descricaoFaixa": "5 acertos", "numeroDeGanhadores": ganhadores}]
    with pytest.raises(FonteCaixaError):
        ganhadores_da_quina(DIA, transport=TransporteFalso(body=corpo(listaRateioPremio=faixas)))


def test_zero_ganhadores_e_valor_valido_nao_erro() -> None:
    """Ninguém acertar a quina é um desfecho legítimo — e raro, mas acontece."""
    faixas = [{"descricaoFaixa": "5 acertos", "numeroDeGanhadores": 0}]
    assert ganhadores_da_quina(
        DIA, transport=TransporteFalso(body=corpo(listaRateioPremio=faixas))
    ) == pytest.approx(0.0)


@pytest.mark.parametrize(
    "status,body",
    [(500, b"erro"), (403, b"bloqueado"), (200, b"nao-json"), (200, b"[1,2,3]"), (200, b"{}")],
)
def test_resposta_invalida_levanta(status: int, body: bytes) -> None:
    with pytest.raises(FonteCaixaError):
        soma_das_dezenas(DIA, transport=TransporteFalso(status=status, body=body))


def test_erro_da_caixa_e_capturavel_pela_raiz_comum() -> None:
    with pytest.raises(FonteError):
        soma_das_dezenas(DIA, transport=TransporteFalso(status=500))
