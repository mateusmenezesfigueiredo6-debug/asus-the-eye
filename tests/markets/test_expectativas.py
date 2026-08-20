# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes para expectativas.py — valida comportamento fail-closed."""

from __future__ import annotations

from datetime import date

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


# ------------------------------------------------------------ ligada ao resolvedor


def test_valor_absurdo_da_fonte_nao_escreve_nada(tmp_path) -> None:
    """A prova que importa: a trava está LIGADA ao caminho real de ingestão.

    Um mecanismo de validação que existe mas ninguém chama é decoração — a
    mesma doença que `estado` tinha antes de a medição validá-lo. Este teste
    falha se alguém desligar a expectativa do resolvedor.
    """
    import json

    from asus_theye.markets.live import resolver_pendentes

    store = tmp_path / "registro.json"
    registro = {
        "versao": 1,
        "mercados": [
            {
                "claim_id": "MACRO-01::2026-07",
                "market_area_id": "macroeconomia",
                "question": "IPCA de 2026-07 fica em 0,50% ou mais?",
                "deadline": "2026-07-31",
                "probability": 0.5,
                "resolution_source": "api.bcb.gov.br (SGS)",
                "created_at": "2026-07-01T00:00:00Z",
                "mes_referencia": "2026-07",
                "limiar": 0.5,
                "criterio": "IPCA mensal >= 0.50%",
                "serie_sgs": 433,
                "estado": "ABERTO",
                "tentativas": [],
            }
        ],
    }
    store.write_text(json.dumps(registro), encoding="utf-8")
    antes = json.loads(store.read_text(encoding="utf-8"))

    # a fonte devolve algo impossível para IPCA mensal (mudança de unidade? bug?)
    resultado = resolver_pendentes(
        store=store, fetcher=lambda _mes: 4200.0, hoje=date(2026, 8, 20), emitir_seguinte=False
    )

    acoes = {a["acao"] for a in resultado}
    assert "recusado" in acoes, f"a expectativa não barrou: {resultado}"
    assert "liquidado" not in acoes
    # o conteúdo tem de estar intacto — o mercado continua ABERTO, sem desfecho,
    # sem Brier. (A formatação do arquivo pode mudar; o que não pode mudar é o dado.)
    assert json.loads(store.read_text(encoding="utf-8")) == antes, "o dado foi alterado apesar da recusa"


def test_valor_plausivel_passa_e_liquida(tmp_path) -> None:
    """A trava não pode ser tão apertada que impeça o trabalho legítimo."""
    import json

    from asus_theye.markets.live import resolver_pendentes

    store = tmp_path / "registro.json"
    store.write_text(
        json.dumps(
            {
                "versao": 1,
                "mercados": [
                    {
                        "claim_id": "MACRO-01::2026-07",
                        "market_area_id": "macroeconomia",
                        "question": "IPCA de 2026-07 fica em 0,50% ou mais?",
                        "deadline": "2026-07-31",
                        "probability": 0.5,
                        "resolution_source": "api.bcb.gov.br (SGS)",
                        "created_at": "2026-07-01T00:00:00Z",
                        "mes_referencia": "2026-07",
                        "limiar": 0.5,
                        "criterio": "IPCA mensal >= 0.50%",
                        "serie_sgs": 433,
                        "estado": "ABERTO",
                        "tentativas": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    resultado = resolver_pendentes(
        store=store, fetcher=lambda _mes: 0.07, hoje=date(2026, 8, 20), emitir_seguinte=False
    )
    assert "liquidado" in {a["acao"] for a in resultado}
