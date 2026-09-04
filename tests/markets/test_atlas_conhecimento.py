# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do Atlas de Conhecimento (R7.5 alavanca C), escritos a-seco 02/09/2026.

Contra o CONTRATO do módulo, não contra comportamento observado. Rodam na
primeira sessão com shell, junto da suíte.
"""
from pathlib import Path

import pytest

from asus_theye.markets.atlas_conhecimento import AtlasConhecimento, Entrada

CABE = ("segmento;id;tipo;nome;autoria;afiliacao_ou_org;obra_ou_o_que_faz;"
        "url;licenca;ano;premios;criticas_e_validade;rank")


def _escrever(tmp: Path, linhas: list[str]) -> Path:
    p = tmp / "INDICE-MESTRE.csv"
    p.write_text(CABE + "\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    return p


def test_indice_ausente_e_fail_soft(tmp_path):
    a = AtlasConhecimento.carregar(tmp_path / "nao-existe.csv")
    assert len(a) == 0
    assert a.segmentos() == {}
    assert a.topo() == []  # não quebra o motor


def test_carrega_e_consulta(tmp_path):
    p = _escrever(tmp_path, [
        "ia;ia-alan-turing;pessoa;Alan Turing;Alan Turing;Bletchley;teste de Turing;"
        "https://doi.org/x;-;1950;o premio ACM leva seu nome;consenso estabelecido;5",
        "meta;meta-dlrm;algoritmo;DLRM;Meta AI;Meta AI;rede de recomendacao;"
        "https://arxiv.org/abs/1906.00091;aberto;2019;-;base de >60% da inferencia;5",
        "consorcios;consorcios-arxiv;fonte;arXiv;Cornell;Cornell;preprints;"
        "https://arxiv.org/;aberto;-;-;nunca submeter dado do titular;5",
    ])
    a = AtlasConhecimento.carregar(p)
    assert len(a) == 3
    assert a.segmentos() == {"consorcios": 1, "ia": 1, "meta": 1}
    assert len(a.por_tipo("pessoa")) == 1
    assert len(a.por_tipo("algoritmo")) == 1
    assert a.por_segmento("meta")[0].nome == "DLRM"


def test_topo_por_rank(tmp_path):
    p = _escrever(tmp_path, [
        "ml;ml-a;pessoa;A;A;x;o;u;-;2000;-;consenso;5",
        "ml;ml-b;pessoa;B;B;x;o;u;-;2000;-;consenso;3",
        "ml;ml-c;pessoa;C;C;x;o;u;-;2000;-;consenso;4",
    ])
    a = AtlasConhecimento.carregar(p)
    ids = [e.id for e in a.topo("ml", mínimo=4)]
    assert ids == ["ml-a", "ml-c"]  # rank 5 antes de 4; rank 3 fora


def test_proveniencia_e_nunca_executavel(tmp_path):
    p = _escrever(tmp_path, [
        "meta;meta-hstu;algoritmo;HSTU;Meta;Meta;recomendacao sequencial;"
        "https://arxiv.org/abs/2402.17152;aberto;2024;-;+12,4% em A/B real;5",
    ])
    a = AtlasConhecimento.carregar(p)
    e = a.proveniencia("meta-hstu")
    assert isinstance(e, Entrada) and e.tipo == "algoritmo"
    # é metadado de proveniência — o Atlas de conhecimento não tem método de rodar
    assert not hasattr(a, "executar")
    assert a.proveniencia("inexistente") is None


def test_auditoria_sem_critica(tmp_path):
    p = _escrever(tmp_path, [
        "ia;ia-x;pessoa;X;X;org;obra;u;-;2020;-;consenso estabelecido;5",
        "ia;ia-y;pessoa;Y;Y;org;obra;u;-;2020;-;-;4",
        "ia;ia-z;pessoa;Z;Z;org;obra;u;-;2020;-;;3",
    ])
    a = AtlasConhecimento.carregar(p)
    sem = {e.id for e in a.sem_critica()}
    assert sem == {"ia-y", "ia-z"}  # "-" e vazio contam como sem crítica


def test_recusa_indice_com_esquema_errado(tmp_path):
    p = tmp_path / "INDICE-MESTRE.csv"
    p.write_text("segmento;nome;rank\nia;Turing;5\n", encoding="utf-8")
    with pytest.raises(ValueError):
        AtlasConhecimento.carregar(p)
