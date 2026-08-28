# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ponte real da seleção: edge só com comparador; convicção declarada sem ele."""

from __future__ import annotations

import json

import pytest

from asus_theye.benchmark.selecao_carteira import selecionar_carteira
from asus_theye.benchmark.selecao_real import carregar_candidatos_reais


def _registro(tmp_path, mercados):
    caminho = tmp_path / "registro.json"
    caminho.write_text(json.dumps({"versao": 1, "mercados": mercados}), encoding="utf-8")
    return caminho


ABERTOS = [
    {"claim_id": "MACRO-01::2026-08", "estado": "ABERTO", "probability": 0.166667, "question": "IPCA >= 0,50%?"},
    {"claim_id": "JUROS-01::2026-09", "estado": "ABERTO", "probability": 0.75, "question": "Selic >= 14%?"},
    {"claim_id": "CAMBIO-01::2026-09", "estado": "ABERTO", "probability": 0.875, "question": "PTAX >= 5,17?"},
    {"claim_id": "VELHO-01::2026-07", "estado": "LIQUIDADO", "probability": 1.0, "question": "já foi"},
]


def test_sem_comparador_usa_conviccao_declarada(tmp_path):
    registro = _registro(tmp_path, ABERTOS)
    candidatos, correlacao, diag = carregar_candidatos_reais(registro, tmp_path / "nao-existe.jsonl")
    assert diag["modo"] == "confianca"
    assert len(candidatos) == 3  # LIQUIDADO fica de fora
    valores = {c.codigo: c.edge for c in candidatos}
    assert valores["CAMBIO-01::2026-09"] == pytest.approx(0.75)
    assert valores["MACRO-01::2026-08"] == pytest.approx(0.666666, abs=1e-5)
    assert any("NÃO é vantagem" in lim for lim in diag["limitacoes"])


def test_com_comparador_completo_calcula_edge(tmp_path):
    registro = _registro(tmp_path, ABERTOS)
    comparador = tmp_path / "comparador.jsonl"
    linhas = [
        {"claim_id": "MACRO-01::2026-08", "p_comparador": 0.20},
        {"claim_id": "JUROS-01::2026-09", "p_comparador": 0.60},
        {"claim_id": "CAMBIO-01::2026-09", "p_comparador": 0.90},
    ]
    comparador.write_text("\n".join(json.dumps(linha) for linha in linhas), encoding="utf-8")
    candidatos, _, diag = carregar_candidatos_reais(registro, comparador)
    assert diag["modo"] == "edge"
    valores = {c.codigo: c.edge for c in candidatos}
    assert valores["JUROS-01::2026-09"] == pytest.approx(0.15)
    assert valores["CAMBIO-01::2026-09"] == pytest.approx(-0.025)


def test_comparador_parcial_nao_vira_edge(tmp_path):
    registro = _registro(tmp_path, ABERTOS)
    comparador = tmp_path / "comparador.jsonl"
    comparador.write_text(json.dumps({"claim_id": "JUROS-01::2026-09", "p_comparador": 0.6}), encoding="utf-8")
    _, _, diag = carregar_candidatos_reais(registro, comparador)
    assert diag["modo"] == "confianca"
    assert diag["com_comparador"] == 1


def test_sem_mercado_aberto_recusa(tmp_path):
    registro = _registro(tmp_path, [{"claim_id": "X", "estado": "LIQUIDADO", "probability": 1.0}])
    with pytest.raises(ValueError, match="nada a selecionar"):
        carregar_candidatos_reais(registro, tmp_path / "c.jsonl")


def test_probability_invalida_recusa(tmp_path):
    registro = _registro(tmp_path, [{"claim_id": "X::1", "estado": "ABERTO", "probability": 1.5}])
    with pytest.raises(ValueError, match="probability inválida"):
        carregar_candidatos_reais(registro, tmp_path / "c.jsonl")


def test_ponta_a_ponta_com_selecao(tmp_path):
    registro = _registro(tmp_path, ABERTOS)
    candidatos, correlacao, _ = carregar_candidatos_reais(registro, tmp_path / "c.jsonl")
    resultado = selecionar_carteira(candidatos, correlacao=correlacao, k=2)
    assert resultado["bate_otimo"] is True
    # maiores convicções: CAMBIO (0.75) e MACRO (0.667)
    assert sorted(resultado["selecao"]) == ["CAMBIO-01::2026-09", "MACRO-01::2026-08"]
