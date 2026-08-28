# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seleção de carteira QAOA: honestidade contra o ótimo exato e regras de domínio."""

from __future__ import annotations

import json

import pytest

from asus_theye.audit import AuditLedger
from asus_theye.benchmark.selecao_carteira import (
    Candidato,
    candidatos_demo,
    selecionar_carteira,
)


def test_demo_recuperada_escolhe_exatamente_k_e_bate_o_otimo():
    candidatos, correlacao = candidatos_demo()
    resultado = selecionar_carteira(candidatos, correlacao=correlacao, k=3)
    assert len(resultado["selecao"]) == 3
    assert resultado["bate_otimo"] is True
    assert resultado["selecao"] == resultado["selecao_otima"]
    assert resultado["hardware_execution"] is False


def test_penalidade_de_correlacao_evita_par_gemeo():
    # A e B têm os dois maiores edges, mas são quase a mesma posição
    # (corr 0.9, riscos altos): a carteira ótima troca B por C.
    candidatos = [
        Candidato("A", 0.20, 0.9),
        Candidato("B", 0.19, 0.9),
        Candidato("C", 0.10, 0.1),
        Candidato("D", 0.01, 0.1),
    ]
    resultado = selecionar_carteira(
        candidatos, correlacao={(0, 1): 0.9}, k=2, lam=2.0
    )
    assert resultado["selecao_otima"] == ["A", "C"]
    assert resultado["bate_otimo"] is True


def test_determinismo_com_mesma_semente():
    candidatos, correlacao = candidatos_demo()
    primeiro = selecionar_carteira(candidatos, correlacao=correlacao, seed=11)
    segundo = selecionar_carteira(candidatos, correlacao=correlacao, seed=11)
    primeiro.pop("execution_time_ms")
    segundo.pop("execution_time_ms")
    assert primeiro == segundo


def test_sela_no_ledger(tmp_path):
    candidatos, correlacao = candidatos_demo()
    ledger = AuditLedger(tmp_path / "ledger.jsonl")
    resultado = selecionar_carteira(candidatos, correlacao=correlacao, ledger=ledger)
    linhas = (tmp_path / "ledger.jsonl").read_text().splitlines()
    assert len(linhas) == 1
    evento = json.loads(linhas[0])
    assert evento["event"] == "benchmark.selecao_carteira"
    assert evento["payload"]["selecao"] == resultado["selecao"]


@pytest.mark.parametrize(
    "kwargs, mensagem",
    [
        ({"k": 0}, "k deve"),
        ({"k": 9}, "k deve"),
        ({"shots": 0}, "positivos"),
    ],
)
def test_validacoes_de_parametros(kwargs, mensagem):
    candidatos, correlacao = candidatos_demo()
    with pytest.raises(ValueError, match=mensagem):
        selecionar_carteira(candidatos, correlacao=correlacao, **kwargs)


def test_recusa_codigos_duplicados():
    with pytest.raises(ValueError, match="únicos"):
        selecionar_carteira([Candidato("X", 0.1, 0.1), Candidato("X", 0.2, 0.2)], k=1)


def test_recusa_correlacao_fora_do_dominio():
    candidatos = [Candidato("A", 0.1, 0.1), Candidato("B", 0.2, 0.2)]
    with pytest.raises(ValueError, match="par de correlação inválido"):
        selecionar_carteira(candidatos, correlacao={(0, 5): 0.4}, k=1)
    with pytest.raises(ValueError, match="valores diferentes"):
        selecionar_carteira(candidatos, correlacao={(0, 1): 0.4, (1, 0): 0.2}, k=1)


def test_recusa_mais_que_o_maximo_de_qubits():
    candidatos = [Candidato(f"C{i}", 0.01 * i, 0.1) for i in range(13)]
    with pytest.raises(ValueError, match="no máximo"):
        selecionar_carteira(candidatos, k=3)


def test_risco_fora_da_faixa_e_recusado_na_construcao():
    with pytest.raises(ValueError, match="risco"):
        Candidato("A", 0.1, 1.5)
