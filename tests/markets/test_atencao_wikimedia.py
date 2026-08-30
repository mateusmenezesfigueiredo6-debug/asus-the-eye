# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Atenção Wikimedia — travando os achados da revisão do Copilot de 30/08/2026.

Este módulo rodava em produção há horas sem suíte de testes própria — lacuna de
disciplina, corrigida aqui junto com os defeitos que a revisão externa achou.

Os quatro casos centrais, todos consequência do mesmo padrão de erro:
tratar resposta MAL-FORMADA como se fosse resposta AUSENTE. É a mentira mais
perigosa deste projeto — "não sei" e "recebi lixo" não podem parecer a mesma
coisa.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from asus_theye.markets.atencao_wikimedia import (
    AtencaoError,
    ArtigoAmbiguoError,
    de_log_razao,
    excedente_sobre_base,
    exigir_artigo_confiavel,
    fatia_de_atencao,
    log_razao,
    verificar_artigo,
    visualizacoes,
)
from asus_theye.net.http import HttpResponse


class Transporte:
    def __init__(self, *, status=200, body=b"{}"):
        self.status, self.body = status, body
        self.urls: list[str] = []

    def request(self, url, *, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
        self.urls.append(url)
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


def resposta_query(*, missing=False, invalid=False, redirects=False, titulo="X"):
    pagina = {"title": titulo}
    if missing:
        pagina["missing"] = ""
    if invalid:
        pagina["invalid"] = ""
    corpo = {"query": {"pages": {"1": pagina}}}
    if redirects:
        corpo["query"]["redirects"] = [{"from": "Y", "to": titulo}]
    return json.dumps(corpo).encode()


# --------------------------------------------------------------------------
# HIGH — projeto não validado em verificar_artigo (achado #3)


def test_verificar_artigo_recusa_projeto_malformado():
    with pytest.raises(AtencaoError, match="projeto"):
        verificar_artigo("X", projeto="não-é-um-projeto", transport=Transporte())


def test_verificar_artigo_aceita_projeto_valido():
    a = verificar_artigo("X", transport=Transporte(body=resposta_query(titulo="X")))
    assert a.titulo_real == "X"


# --------------------------------------------------------------------------
# HIGH — título com "|" consulta múltiplas páginas em silêncio


def test_titulo_com_pipe_e_recusado():
    """A API MediaWiki trata "|" como separador de múltiplos títulos.

    Sem a guarda, ``paginas[0]`` pegaria a primeira por ordem do dict — não
    necessariamente a pedida — e confirmaria "confiável" o artigo errado.
    """
    with pytest.raises(AtencaoError, match=r"\|"):
        verificar_artigo("Lula|Bolsonaro", transport=Transporte())


# --------------------------------------------------------------------------
# MEDIUM — chave "invalid" do MediaWiki não tratada


def test_titulo_sintaticamente_invalido_e_recusado():
    """"invalid" não é "existe: sim" nem "existe: não" — é "nem processei".

    Sem checar, esse caso caía no ramo "existe" por omissão: nem "missing"
    nem "invalid" apareciam, e ``existe = "missing" not in p`` dava True.
    """
    t = Transporte(body=resposta_query(invalid=True))
    with pytest.raises(AtencaoError, match="inválido"):
        verificar_artigo("###", transport=t)


def test_artigo_ausente_e_recusado_por_exigir_confiavel():
    t = Transporte(body=resposta_query(missing=True, titulo="X"))
    with pytest.raises(ArtigoAmbiguoError, match="não existe"):
        exigir_artigo_confiavel("X", transport=t)


def test_artigo_que_redireciona_e_recusado_com_o_destino():
    t = Transporte(body=resposta_query(redirects=True, titulo="Teuthida"))
    with pytest.raises(ArtigoAmbiguoError, match="Teuthida"):
        exigir_artigo_confiavel("Lula", transport=t)


def test_artigo_confiavel_e_aceito():
    t = Transporte(body=resposta_query(titulo="Luiz Inácio Lula da Silva"))
    assert exigir_artigo_confiavel("Lula", transport=t) == "Luiz Inácio Lula da Silva"


# --------------------------------------------------------------------------
# MEDIUM — item malformado na série era descartado em silêncio (achado #8)


def _serie_corpo(itens):
    return json.dumps({"items": itens}).encode()


def test_item_nao_dicionario_na_serie_levanta_em_vez_de_descartar():
    """O defeito que contradizia a própria doutrina do arquivo.

    "Dia ausente é ausência, nunca zero" — mas descartar um item corrompido em
    silêncio tratava resposta QUEBRADA como dia legitimamente não publicado.
    """
    t = Transporte(body=_serie_corpo(["não é um objeto"]))
    with pytest.raises(AtencaoError, match="não é objeto"):
        visualizacoes("X", date(2022, 10, 1), date(2022, 10, 1), transport=t)


def test_serie_bem_formada_e_lida_corretamente():
    itens = [{"timestamp": "2022100100", "views": 267873}]
    t = Transporte(body=_serie_corpo(itens))
    serie = visualizacoes("X", date(2022, 10, 1), date(2022, 10, 1), transport=t)
    assert serie == {date(2022, 10, 1): 267873}


def test_visualizacao_negativa_e_recusada():
    itens = [{"timestamp": "2022100100", "views": -5}]
    t = Transporte(body=_serie_corpo(itens))
    with pytest.raises(AtencaoError, match="negativa"):
        visualizacoes("X", date(2022, 10, 1), date(2022, 10, 1), transport=t)


def test_periodo_invertido_e_recusado():
    with pytest.raises(AtencaoError, match="invertido"):
        visualizacoes("X", date(2022, 10, 2), date(2022, 10, 1), transport=Transporte())


# --------------------------------------------------------------------------
# A geometria composicional (log-razão) e o excedente sobre base


def test_log_razao_fecha_o_ciclo_de_ida_e_volta():
    c = {"A": 0.5, "B": 0.3, "C": 0.2}
    assert de_log_razao(log_razao(c)) == pytest.approx(c)


def test_excedente_sobre_base_subtrai_fama_pre_existente():
    atual = {"A": [300, 320], "B": [50, 60]}
    base = {"A": [100, 100], "B": [40, 40]}
    exc = excedente_sobre_base(atual, base)
    assert exc["A"] > exc["B"]


def test_excedente_nao_fica_negativo():
    atual = {"A": [10, 10]}
    base = {"A": [100, 100]}
    assert excedente_sobre_base(atual, base)["A"] == 0.0


def test_excedente_exige_os_mesmos_candidatos_nos_dois_lados():
    with pytest.raises(AtencaoError, match="diferentes"):
        excedente_sobre_base({"A": [1]}, {"B": [1]})


def test_fatia_de_atencao_soma_total_zero_e_indisponibilidade():
    with pytest.raises(AtencaoError, match="zero"):
        fatia_de_atencao({"A": 0.0, "B": 0.0})


def test_de_log_razao_nao_estoura_com_composicao_quase_degenerada():
    """O bug real achado pela varredura estrutural de 30/08/2026.

    de_clr (modelo_eleitoral.py) subtrai o máximo antes de exponenciar, desde
    o incidente do beta 8,5. Esta função é cópia da mesma matemática, mas
    nasceu sem a proteção — e com coordenadas grandes, math.exp() estourava em
    OverflowError cru, não AtencaoError.
    """
    de_log_razao({"A": 750.0, "B": -375.0, "C": -375.0})  # não deve levantar


def test_de_log_razao_fecha_o_ciclo_de_ida_e_volta_com_valores_grandes():
    c = log_razao({"A": 0.97, "B": 0.02, "C": 0.01})
    grande = {k: v * 50 for k, v in c.items()}
    fatias = de_log_razao(grande)
    assert sum(fatias.values()) == pytest.approx(1.0)
    assert fatias["A"] > fatias["B"] > fatias["C"]


def test_de_log_razao_recusa_coordenadas_vazias():
    with pytest.raises(AtencaoError, match="vazias"):
        de_log_razao({})
