"""Testes da politica de dado pessoal — a regra tem que viver no codigo.

Defeito real que estes testes travam: a ontologia declarava que previdenciario,
familia e sucessoes nao devem ter extracao (a parte nomeada e pessoa fisica),
mas o codigo ignorava a declaracao e caia no caminho generico, publicando
excertos com nome completo de beneficiario.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.comercial.radar_juridico import ONT, gerar, render_recusado

PROTEGIDOS = [n for n in ONT["nichos"] if n.get("tipo_parte") == "fisica"]
JURIDICOS = [n for n in ONT["nichos"] if n.get("tipo_parte") == "juridica"]


def test_ha_nichos_declarados_como_pessoa_fisica():
    assert PROTEGIDOS, "a politica so vale se algum nicho estiver marcado"
    assert {n["niche_id"] for n in PROTEGIDOS} >= {"previdenciario", "familia", "sucessoes"}


@pytest.mark.parametrize("nicho", PROTEGIDOS, ids=lambda n: n["niche_id"])
def test_nicho_protegido_declara_o_motivo(nicho):
    assert nicho.get("sem_extracao_motivo"), "recusar sem dizer por que nao ensina nada"


@pytest.mark.parametrize("nicho", PROTEGIDOS, ids=lambda n: n["niche_id"])
def test_pagina_de_recusa_nao_traz_trecho_de_diario(nicho):
    saida = render_recusado(nicho)
    assert "nao e coberto" in saida
    assert "<article class=lead>" not in saida, "recusa nao pode conter lead"
    assert "Conferir no diario oficial" not in saida


@pytest.mark.parametrize("nicho", PROTEGIDOS, ids=lambda n: n["niche_id"])
def test_nicho_protegido_nao_recebe_padrao_de_extracao(nicho):
    assert "regex_entidade" not in nicho, (
        "marcar como pessoa fisica e depois dar regex de extracao e contradicao")


def test_gerar_nicho_protegido_nao_consulta_a_api(monkeypatch):
    """A recusa acontece ANTES da busca: nem chega a baixar o ato."""
    def nao_deve_ser_chamado(*_a, **_k):
        raise AssertionError("nicho protegido nao pode consultar a fonte")

    monkeypatch.setattr("apps.comercial.radar_juridico.buscar", nao_deve_ser_chamado)
    destino = gerar(PROTEGIDOS[0]["niche_id"], 14)
    assert destino.exists()
    assert "nao e coberto" in destino.read_text(encoding="utf-8")


def test_edicao_de_nicho_protegido_nao_contem_cpf_nem_nome_completo():
    destino = gerar("previdenciario", 14)
    texto = destino.read_text(encoding="utf-8")
    assert not re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-\d{2}\b", texto)
    # tres ou mais nomes proprios seguidos em caixa alta e assinatura de nome completo
    assert not re.search(r"\b[A-ZÀ-Ú]{3,}\s+[A-ZÀ-Ú]{2,}\s+(?:DA|DE|DOS)\s+[A-ZÀ-Ú]{3,}", texto)


@pytest.mark.parametrize("nicho", JURIDICOS, ids=lambda n: n["niche_id"])
def test_nicho_juridico_tem_padrao_e_filtro_de_ruido(nicho):
    assert nicho.get("regex_entidade"), "sem padrao, o nicho entrega excerto bruto"
    assert nicho.get("regex_ruido"), "sem filtro, texto padrao de edital vira lead"


def test_politica_esta_documentada_na_ontologia():
    assert "politica_extracao" in ONT
    assert "pessoa juridica" in ONT["politica_extracao"]
