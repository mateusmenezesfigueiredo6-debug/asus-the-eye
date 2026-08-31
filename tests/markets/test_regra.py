# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da regra de resolução — legível por máquina e, sobretudo, executável."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.markets.regra import RegraError, avaliar, montar_regra, texto, validar_regra

REGRA_IPCA = {
    "versao_schema": 1,
    "fonte": "api.bcb.gov.br (SGS)",
    "serie": 433,
    "indicador": "IPCA mensal",
    "periodo_referencia": "2026-08",
    "operador": ">=",
    "limiar": 0.5,
    "unidade": "percentual_mensal",
    "quando_indisponivel": "UNKNOWN",
}


# ------------------------------------------------------------ avaliação


def test_avaliar_decide_o_desfecho() -> None:
    assert avaliar(REGRA_IPCA, 0.58) == 1
    assert avaliar(REGRA_IPCA, 0.07) == 0


def test_limiar_exato_conta_como_verdadeiro_com_maior_ou_igual() -> None:
    """A fronteira é onde regra ambígua vira disputa — aqui ela é explícita."""
    assert avaliar(REGRA_IPCA, 0.5) == 1
    assert avaliar(REGRA_IPCA | {"operador": ">"}, 0.5) == 0


def test_valor_ausente_e_unknown_nunca_zero() -> None:
    """Liquidar sem dado é fabricar Brier. UNKNOWN é resposta; zero é mentira."""
    assert avaliar(REGRA_IPCA, None) is None


def test_todos_os_operadores_admitidos_funcionam() -> None:
    assert avaliar(REGRA_IPCA | {"operador": "<="}, 0.5) == 1
    assert avaliar(REGRA_IPCA | {"operador": "<"}, 0.5) == 0


# ------------------------------------------------------------ schema


def test_regra_sem_campo_obrigatorio_levanta() -> None:
    incompleta = {k: v for k, v in REGRA_IPCA.items() if k != "limiar"}
    with pytest.raises(RegraError, match="obrigatório"):
        validar_regra(incompleta)


def test_operador_nao_admitido_levanta() -> None:
    with pytest.raises(RegraError, match="operador"):
        validar_regra(REGRA_IPCA | {"operador": "=="})


def test_unidade_nao_admitida_levanta() -> None:
    """14,00 em % a.a. e 14,00 em R$ são perguntas diferentes — a unidade importa."""
    with pytest.raises(RegraError, match="unidade"):
        validar_regra(REGRA_IPCA | {"unidade": "sei_la"})


def test_periodo_malformado_levanta() -> None:
    with pytest.raises(RegraError, match="periodo_referencia"):
        validar_regra(REGRA_IPCA | {"periodo_referencia": "agosto de 2026"})


def test_politica_de_indisponivel_nao_pode_ser_trocada() -> None:
    with pytest.raises(RegraError, match="quando_indisponivel"):
        validar_regra(REGRA_IPCA | {"quando_indisponivel": "zero"})


def test_fonte_proibida_levanta() -> None:
    """Comparador nunca resolve — a doutrina vale também dentro da regra."""
    with pytest.raises(RegraError, match="proibida"):
        validar_regra(REGRA_IPCA | {"fonte": "Chaox"})


def test_fonte_vazia_levanta() -> None:
    with pytest.raises(RegraError, match="proveniência"):
        validar_regra(REGRA_IPCA | {"fonte": "   "})


def test_versao_de_schema_desconhecida_levanta() -> None:
    with pytest.raises(RegraError, match="versao_schema"):
        validar_regra(REGRA_IPCA | {"versao_schema": 99})


def test_montar_regra_nunca_devolve_invalida() -> None:
    with pytest.raises(RegraError, match="unidade"):
        montar_regra(
            fonte="api.bcb.gov.br (SGS)",
            serie=433,
            indicador="IPCA mensal",
            periodo_referencia="2026-08",
            limiar=0.5,
            unidade="inexistente",
        )


# ------------------------------------------------------------ texto derivado


def test_texto_e_derivado_da_estrutura() -> None:
    """Prosa e estrutura não podem divergir porque a prosa nasce da estrutura."""
    assert texto(REGRA_IPCA) == "IPCA mensal >= 0.50% (2026-08, fonte: api.bcb.gov.br (SGS))"
    brl = REGRA_IPCA | {"unidade": "brl", "limiar": 5.17, "indicador": "PTAX venda"}
    assert "R$ 5.17" in texto(brl)


# ------------------------------------------------------------ integração real


def test_a_regra_reproduz_o_desfecho_da_liquidacao_real() -> None:
    """A prova que importa: a regra decide o MESMO que foi gravado no ledger.

    Se a regra e o resolvedor pudessem divergir, este teste acusaria. Como o
    resolvedor agora chama ``avaliar``, eles são a mesma coisa — e este teste
    guarda essa propriedade contra regressão.
    """
    caminho = Path("reports/markets/resolucoes.jsonl")
    if not caminho.exists():
        pytest.skip("sem liquidações reais no repositório")
    linhas = [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]
    assert linhas, "resolucoes.jsonl vazio"

    # Linhas antigas não carregam limiar/mes_referencia — os termos do claim
    # vivem no registro, que é a fonte de verdade deles. Buscar ali é honesto;
    # extrair da prosa do critério seria voltar ao problema que a regra resolve.
    registro = json.loads(Path("reports/markets/registro.json").read_text(encoding="utf-8"))
    por_id = {m["claim_id"]: m for m in registro.get("mercados", [])}

    conferidas = 0
    for linha in linhas:
        mercado = por_id.get(linha["claim_id"])
        if mercado is None:
            continue
        regra = montar_regra(
            fonte=str(linha["resolution_source"]),
            serie=int(mercado["serie_sgs"]),
            indicador="IPCA mensal",
            periodo_referencia=str(mercado["mes_referencia"]),
            limiar=float(mercado["limiar"]),
            unidade="percentual_mensal",
        )
        assert avaliar(regra, float(linha["valor_observado"])) == int(linha["outcome"]), (
            f"{linha['claim_id']}: a regra discorda do desfecho gravado"
        )
        conferidas += 1
    assert conferidas, "nenhuma liquidação pôde ser conferida contra a regra — teste seria vazio"


def test_todo_claim_vivo_tem_regra_valida() -> None:
    """Nenhum mercado no registro pode ficar sem regra verificável."""
    caminho = Path("reports/markets/registro.json")
    if not caminho.exists():
        pytest.skip("sem registro de mercados no repositório")
    mercados = json.loads(caminho.read_text(encoding="utf-8")).get("mercados", [])
    for mercado in mercados:
        if "regra" not in mercado:
            continue  # claim antigo: a regra é derivada na liquidação (ver live.py)
        validar_regra(mercado["regra"])
        assert avaliar(mercado["regra"], float(mercado["limiar"])) == 1  # limiar exato com >=
