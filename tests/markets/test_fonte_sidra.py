# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector IBGE/SIDRA — com foco na guarda que justifica sua existência.

O que se prova aqui, além do caminho feliz, é que o conector **recusa** liquidar
quando o código deixa de significar o que o mercado diz medir. Sem isso, uma
reorganização de classificação no IBGE liquidaria contratos contra o item
errado em silêncio — e o que entra selado não sai sem expurgo.
"""

from __future__ import annotations

import json

import pytest

from asus_theye.markets.fonte_base import FonteError
from asus_theye.markets.fonte_sidra import FonteSidraError, variacao_mensal
from asus_theye.net.http import HttpResponse

CABECALHO = {
    "NC": "Nível Territorial (Código)",
    "V": "Valor",
    "D3C": "Mês (Código)",
    "D3N": "Mês",
    "D4C": "Geral, grupo, subgrupo, item e subitem (Código)",
    "D4N": "Geral, grupo, subgrupo, item e subitem",
    "MN": "Unidade de Medida",
}


def corpo(**sobrescreve: object) -> bytes:
    """Resposta no formato real do SIDRA, conferido ao vivo em 29/08/2026."""
    linha = {
        "NC": "1",
        "NN": "Brasil",
        "MC": "2",
        "MN": "%",
        "V": "3.09",
        "D3C": "202607",
        "D3N": "julho 2026",
        "D4C": "7484",
        "D4N": "2202.Energia elétrica residencial",
    }
    linha.update(sobrescreve)  # type: ignore[arg-type]
    return json.dumps([CABECALHO, linha]).encode("utf-8")


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.status, self.body = status, body if body is not None else corpo()
        self.urls: list[str] = []

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        self.urls.append(url)
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


LUZ = {"codigo": 7484, "nome_esperado": "Energia elétrica residencial"}


def test_le_a_variacao_e_monta_a_url_exata() -> None:
    transporte = TransporteFalso()
    assert variacao_mensal("2026-07", transport=transporte, **LUZ) == pytest.approx(3.09)
    assert transporte.urls == [
        "https://apisidra.ibge.gov.br/values/t/7060/n1/all/v/63/p/202607/c315/7484"
    ]


def test_mes_nao_publicado_e_none_e_nao_erro() -> None:
    # O SIDRA devolve SÓ o cabeçalho quando o mês ainda não saiu. É UNKNOWN.
    so_cabecalho = json.dumps([CABECALHO]).encode("utf-8")
    assert variacao_mensal("2026-12", transport=TransporteFalso(body=so_cabecalho), **LUZ) is None


@pytest.mark.parametrize("ausente", ["...", "-", "..", "X", ""])
def test_celula_vazia_e_none_nunca_zero(ausente: str) -> None:
    assert variacao_mensal("2026-07", transport=TransporteFalso(body=corpo(V=ausente)), **LUZ) is None


def test_codigo_que_mudou_de_significado_recusa_liquidar() -> None:
    """A guarda central: o IBGE devolveu outro item para o mesmo código."""
    trocado = corpo(D4N="2203.Consertos e manutenção")
    with pytest.raises(FonteSidraError, match="mudou de significado"):
        variacao_mensal("2026-07", transport=TransporteFalso(body=trocado), **LUZ)


def test_codigo_diferente_do_pedido_levanta() -> None:
    with pytest.raises(FonteSidraError, match="não o"):
        variacao_mensal("2026-07", transport=TransporteFalso(body=corpo(D4C="7482")), **LUZ)


def test_mes_fora_do_pedido_levanta() -> None:
    with pytest.raises(FonteSidraError, match="fora do mês"):
        variacao_mensal("2026-07", transport=TransporteFalso(body=corpo(D3C="202606")), **LUZ)


def test_unidade_trocada_na_fonte_levanta() -> None:
    """Se a fonte passar a publicar índice em vez de %, o número muda de sentido."""
    with pytest.raises(FonteSidraError, match="unidade mudou"):
        variacao_mensal("2026-07", transport=TransporteFalso(body=corpo(MN="Índice")), **LUZ)


def test_acento_e_caixa_nao_quebram_a_comparacao_de_nome() -> None:
    assert (
        variacao_mensal(
            "2026-07", transport=TransporteFalso(), codigo=7484, nome_esperado="ENERGIA ELETRICA RESIDENCIAL"
        )
        == pytest.approx(3.09)
    )


@pytest.mark.parametrize(
    "status,body",
    [
        (500, b"erro"),
        (404, b"nao achei"),
        (200, b"nao-json"),
        (200, b'{"nao":"lista"}'),
        (200, b"[]"),
    ],
)
def test_resposta_invalida_levanta(status: int, body: bytes) -> None:
    with pytest.raises(FonteSidraError):
        variacao_mensal("2026-07", transport=TransporteFalso(status=status, body=body), **LUZ)


def test_mais_de_uma_observacao_levanta() -> None:
    duas = json.dumps([CABECALHO, json.loads(corpo())[1], json.loads(corpo())[1]]).encode("utf-8")
    with pytest.raises(FonteSidraError, match="vieram 2"):
        variacao_mensal("2026-07", transport=TransporteFalso(body=duas), **LUZ)


@pytest.mark.parametrize("mes", ["2026-13", "2026", "julho/2026", "2026-00"])
def test_mes_em_formato_invalido_levanta(mes: str) -> None:
    with pytest.raises(FonteSidraError):
        variacao_mensal(mes, transport=TransporteFalso(), **LUZ)


def test_erro_do_sidra_e_capturavel_pela_raiz_comum() -> None:
    """Quem resolve mercados captura FonteError; conector novo tem de caber nela."""
    with pytest.raises(FonteError):
        variacao_mensal("2026-07", transport=TransporteFalso(status=500), **LUZ)
