# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes para expectativas.py — valida comportamento fail-closed."""

from __future__ import annotations

import pytest

from asus_theye.markets.expectativas import (
    EXPECTATIVAS,
    ExpectativaViolada,
    FaixaNumerica,
    verificar,
)

# ---------------------------------------------------------------------------
# FaixaNumerica.validar
# ---------------------------------------------------------------------------


def test_valor_dentro_da_faixa_passa() -> None:
    fx = FaixaNumerica(minimo=-5.0, maximo=15.0)
    fx.validar("ipca_mensal", 0.5)  # não levanta


def test_valor_none_aceito_quando_permite_none() -> None:
    fx = FaixaNumerica(minimo=-5.0, maximo=15.0, permite_none=True)
    fx.validar("ipca_mensal", None)  # não levanta


def test_valor_none_rejeitado_quando_nao_permite() -> None:
    fx = FaixaNumerica(minimo=0.0, maximo=100.0, permite_none=False)
    with pytest.raises(ExpectativaViolada, match="ausente"):
        fx.validar("selic_meta", None)


def test_valor_abaixo_do_minimo_levanta() -> None:
    fx = FaixaNumerica(minimo=-5.0, maximo=15.0)
    with pytest.raises(ExpectativaViolada, match="fora da faixa"):
        fx.validar("ipca_mensal", -6.0)


def test_valor_acima_do_maximo_levanta() -> None:
    fx = FaixaNumerica(minimo=-5.0, maximo=15.0)
    with pytest.raises(ExpectativaViolada, match="fora da faixa"):
        fx.validar("ipca_mensal", 16.0)


def test_string_numerica_invalida_levanta() -> None:
    fx = FaixaNumerica(minimo=0.0, maximo=100.0)
    with pytest.raises(ExpectativaViolada, match="tipo inválido"):
        fx.validar("selic_meta", "14.75")


def test_bool_invalido_levanta() -> None:
    fx = FaixaNumerica(minimo=0.0, maximo=1.0)
    with pytest.raises(ExpectativaViolada, match="bool"):
        fx.validar("qualquer", True)


# ---------------------------------------------------------------------------
# verificar — fail-closed e múltiplas violações
# ---------------------------------------------------------------------------


def test_verificar_valido_retorna_resultado_ok() -> None:
    resultado = verificar({"ipca_mensal": 0.44, "selic_meta": 13.75, "ptax_venda": 5.20})
    assert resultado.ok


def test_verificar_com_none_aceito_retorna_ok() -> None:
    resultado = verificar({"ipca_mensal": None})
    assert resultado.ok


def test_verificar_invalido_levanta_e_nao_escreve() -> None:
    """Prova que o store fica intacto: verificar levanta antes de qualquer escrita."""
    store: list[str] = []

    def ingere(valor: float | None) -> None:
        verificar({"ipca_mensal": valor})  # deve levantar
        store.append("escrito")  # nunca deve executar

    with pytest.raises(ExpectativaViolada):
        ingere(999.0)  # valor impossível

    assert store == [], "store deve permanecer intacto quando a expectativa falha"


def test_verificar_indicador_desconhecido_levanta() -> None:
    with pytest.raises(ExpectativaViolada, match="desconhecido"):
        verificar({"indicador_inexistente": 1.0})


def test_verificar_multiple_violacoes_concatenadas() -> None:
    with pytest.raises(ExpectativaViolada) as exc_info:
        verificar({"ipca_mensal": 999.0, "selic_meta": -50.0})
    mensagem = str(exc_info.value)
    assert "ipca_mensal" in mensagem
    assert "selic_meta" in mensagem


# ---------------------------------------------------------------------------
# Constantes declaradas
# ---------------------------------------------------------------------------


def test_expectativas_cobre_indicadores_de_fontes() -> None:
    for nome in ("ipca_mensal", "selic_meta", "ptax_venda"):
        assert nome in EXPECTATIVAS, f"{nome} deve estar em EXPECTATIVAS"


@pytest.mark.parametrize(
    "nome,valor",
    [
        ("ipca_mensal", -4.9),
        ("ipca_mensal", 14.9),
        ("selic_meta", 0.0),
        ("selic_meta", 26.5),
        ("ptax_venda", 0.6),
        ("ptax_venda", 19.9),
    ],
)
def test_valores_historicos_plausíveis_passam(nome: str, valor: float) -> None:
    verificar({nome: valor})


@pytest.mark.parametrize(
    "nome,valor",
    [
        ("ipca_mensal", -5.1),
        ("ipca_mensal", 15.1),
        ("selic_meta", -2.0),
        ("selic_meta", 101.0),
        ("ptax_venda", 0.4),
        ("ptax_venda", 21.0),
    ],
)
def test_valores_implausíveis_levantam(nome: str, valor: float) -> None:
    with pytest.raises(ExpectativaViolada):
        verificar({nome: valor})
