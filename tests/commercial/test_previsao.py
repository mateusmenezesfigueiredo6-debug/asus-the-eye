"""Testes da previsao e do backtest.

Cobrem os tres metodos, a classificacao por regime, e o defeito real encontrado
em revisao: interpolar buracos ANTES do primeiro mes observado inventava
historico que nunca foi medido.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.comercial.previsao import (
    JANELA_TESTE,
    MIN_PONTOS,
    avaliar_nicho,
    backtest,
    holt,
    ingenuo,
    mae,
    mape,
    media3,
)


def meses(n: int) -> list[str]:
    return [f"2024-{i:02d}" if i <= 12 else f"2025-{i - 12:02d}" for i in range(1, n + 1)]


# ------------------------------------------------------------------ metodos
def test_ingenuo_repete_ultimo_valor():
    assert list(ingenuo(np.array([5.0, 9.0, 7.0]), 3)) == [7.0, 7.0, 7.0]


def test_media3_usa_so_os_tres_ultimos():
    y = np.array([100.0, 100.0, 10.0, 20.0, 30.0])
    assert media3(y, 1)[0] == pytest.approx(20.0)


def test_holt_segue_tendencia_de_alta():
    y = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    prev = holt(y, 3)
    assert prev[0] > 50.0, "com tendencia clara de alta, deve projetar acima do ultimo"
    assert prev[2] > prev[0], "o horizonte deve continuar subindo"


def test_holt_nunca_devolve_negativo():
    """Contagem de publicacoes nao pode ser negativa."""
    y = np.array([100.0, 70.0, 40.0, 10.0])
    assert all(v >= 0 for v in holt(y, 6))


def test_holt_com_serie_constante_mantem_o_nivel():
    y = np.array([25.0] * 8)
    assert holt(y, 2)[0] == pytest.approx(25.0, abs=0.5)


# ------------------------------------------------------------------ erros
def test_mae_e_mape():
    real = np.array([10.0, 20.0])
    prev = np.array([12.0, 18.0])
    assert mae(real, prev) == pytest.approx(2.0)
    assert mape(real, prev) == pytest.approx(15.0)


def test_mape_ignora_zeros_em_vez_de_dividir_por_zero():
    real = np.array([0.0, 10.0])
    prev = np.array([5.0, 12.0])
    assert mape(real, prev) == pytest.approx(20.0)


def test_mape_devolve_none_se_tudo_zero():
    assert mape(np.array([0.0, 0.0]), np.array([1.0, 1.0])) is None


# ------------------------------------------------------------------ backtest
def test_backtest_usa_a_janela_de_teste_declarada():
    y = np.array([float(i) for i in range(1, 21)])
    r = backtest(y, "ingenuo")
    assert r["avaliado"] is True
    assert r["n"] == JANELA_TESTE


def test_backtest_nao_olha_o_futuro():
    """Em serie crescente, o ingenuo sempre subestima: prova que so usa passado."""
    y = np.array([float(i) for i in range(1, 21)])
    assert backtest(y, "ingenuo")["mae"] == pytest.approx(1.0)


def test_backtest_de_serie_curta_nao_avalia():
    assert backtest(np.array([1.0, 2.0]), "ingenuo") == {"avaliado": False}


# ------------------------------------------------------------------ avaliacao
def test_serie_curta_e_recusada_sem_inventar_previsao():
    pontos = {m: 5 for m in meses(MIN_PONTOS - 1)}
    r = avaliar_nicho("teste", pontos, meses(MIN_PONTOS - 1), 3)
    assert r["status"] == "serie_insuficiente"
    assert "previsao" not in r, "sem historico bastante, nada pode ser afirmado"


def test_buraco_antes_do_primeiro_mes_e_cortado_nao_inventado():
    """O defeito real: np.interp extrapolava para tras, fabricando historico."""
    ms = meses(18)
    pontos = {m: 50 for m in ms[3:]}  # os 3 primeiros meses nunca medidos
    r = avaliar_nicho("teste", pontos, ms, 1)
    assert r["status"] == "avaliado"
    assert r["pontos_observados"] == 15
    assert r["meses_interpolados"] == 0, "prefixo nao medido deve ser cortado, nao preenchido"


def test_buraco_no_meio_e_interpolado_e_contado():
    ms = meses(18)
    pontos = {m: 50 for m in ms}
    del pontos[ms[8]]
    r = avaliar_nicho("teste", pontos, ms, 1)
    assert r["meses_interpolados"] == 1
    assert r["pontos_observados"] == 17


def test_regime_tendencia_quando_ha_inclinacao():
    ms = meses(24)
    pontos = {m: 10 + 5 * i for i, m in enumerate(ms)}
    r = avaliar_nicho("teste", pontos, ms, 2)
    assert r["regime"] == "tendencia"
    assert r["modelo_campeao"] == "holt"
    assert r["ganho_preditivo"] is True


def test_regime_estavel_quando_serie_e_plana():
    ms = meses(24)
    pontos = {m: 40 for m in ms}
    r = avaliar_nicho("teste", pontos, ms, 2)
    assert r["regime"] in ("estavel", "passeio_aleatorio")
    assert r["ganho_preditivo"] is False, "serie plana nao tem ganho preditivo a declarar"


def test_previsao_tem_o_tamanho_do_horizonte_pedido():
    ms = meses(24)
    pontos = {m: 10 + i for i, m in enumerate(ms)}
    r = avaliar_nicho("teste", pontos, ms, 5)
    assert len(r["previsao"]) == 5
    assert r["horizonte_meses"] == 5


def test_ganho_preditivo_exige_vencer_a_media_simples():
    """Ingenuo vencendo media3 e informacao de regime, nao ganho preditivo."""
    ms = meses(24)
    pontos = {m: (100 if i % 2 else 20) for i, m in enumerate(ms)}
    r = avaliar_nicho("teste", pontos, ms, 1)
    if r["modelo_campeao"] != "holt":
        assert r["ganho_preditivo"] is False
