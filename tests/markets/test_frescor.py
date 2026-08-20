# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes para frescor.py — valida detecção de staleness por fonte."""

from __future__ import annotations

from datetime import date

from asus_theye.markets.frescor import (
    DECLARACOES,
    DeclaracaoFrescor,
    FonteObsoleta,
    fontes_obsoletas,
)

# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

_DECL_TESTE: dict[str, DeclaracaoFrescor] = {
    "fonte_diaria": DeclaracaoFrescor(nome="fonte_diaria", periodicidade_dias=2),
    "fonte_mensal": DeclaracaoFrescor(nome="fonte_mensal", periodicidade_dias=35),
}

_HOJE = date(2026, 8, 20)


# ---------------------------------------------------------------------------
# Fonte em dia
# ---------------------------------------------------------------------------


def test_fonte_em_dia_nao_retorna_obsoleta() -> None:
    # publicou ontem; limite = ontem + 2 dias = amanhã; hoje <= amanhã → em dia
    dados = {"fonte_diaria": date(2026, 8, 19)}
    resultado = fontes_obsoletas(dados, hoje=_HOJE, declaracoes=_DECL_TESTE)
    assert resultado == []


# ---------------------------------------------------------------------------
# Fonte obsoleta
# ---------------------------------------------------------------------------


def test_fonte_obsoleta_retorna_item() -> None:
    # publicou há 40 dias; limite = 40 + 35 = 75 dias, hoje=20→ OK
    # mas se publicou há 60 dias e limite é 35 → obsoleta
    ultima = date(2026, 6, 1)  # ~80 dias antes de 2026-08-20
    dados = {"fonte_mensal": ultima}
    resultado = fontes_obsoletas(dados, hoje=_HOJE, declaracoes=_DECL_TESTE)
    assert len(resultado) == 1
    item = resultado[0]
    assert isinstance(item, FonteObsoleta)
    assert item.nome == "fonte_mensal"
    assert item.data_mais_recente == ultima
    assert item.dias_de_atraso > 0


# ---------------------------------------------------------------------------
# None = nunca publicado → sempre obsoleto
# ---------------------------------------------------------------------------


def test_none_e_sempre_obsoleto() -> None:
    dados = {"fonte_diaria": None}
    resultado = fontes_obsoletas(dados, hoje=_HOJE, declaracoes=_DECL_TESTE)
    assert len(resultado) == 1
    assert resultado[0].data_mais_recente is None


# ---------------------------------------------------------------------------
# Fonte desconhecida é ignorada silenciosamente
# ---------------------------------------------------------------------------


def test_fonte_desconhecida_e_ignorada() -> None:
    dados = {"fonte_inexistente": date(2020, 1, 1)}
    resultado = fontes_obsoletas(dados, hoje=_HOJE, declaracoes=_DECL_TESTE)
    assert resultado == []


# ---------------------------------------------------------------------------
# Declarações padrão cobrem indicadores dos conectores
# ---------------------------------------------------------------------------


def test_declaracoes_padrao_cobrem_indicadores() -> None:
    for nome in ("ipca_mensal", "selic_meta", "ptax_venda"):
        assert nome in DECLARACOES


# ---------------------------------------------------------------------------
# Mistura em dia e obsoleta
# ---------------------------------------------------------------------------


def test_mix_em_dia_e_obsoleta() -> None:
    dados = {
        "fonte_diaria": date(2026, 8, 19),  # em dia
        "fonte_mensal": date(2026, 5, 1),  # obsoleta (~111 dias)
    }
    resultado = fontes_obsoletas(dados, hoje=_HOJE, declaracoes=_DECL_TESTE)
    assert len(resultado) == 1
    assert resultado[0].nome == "fonte_mensal"
