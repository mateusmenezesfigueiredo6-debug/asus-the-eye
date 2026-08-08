"""Testes do monitoramento continuo (etapa 6 do ciclo).

O historico de acuracia e a evidencia de que a plataforma sabe se esta
acertando. Estes testes travam as propriedades que sustentam essa evidencia:
o historico nao pode ser reescrito, a afericao nao pode duplicar, e o alerta
so dispara quando ha base de comparacao.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.comercial import monitoramento
from apps.comercial.monitoramento import FATOR_ALERTA, aferir, alertas, mes_anterior
from apps.comercial.previsao import METODOS


def registro(nid: str, mes: str, erro: float) -> dict:
    return {
        "niche_id": nid,
        "mes_alvo": mes,
        "erro_absoluto": erro,
        "erro_pct": erro,
        "previsto": 100,
        "observado": 100 + erro,
    }


def test_aferir_recalcula_previsao_com_o_modelo_campeao(tmp_path, monkeypatch):
    """O historico deve atribuir ao campeao somente a previsao que ele fez."""
    meses = ["2026-04", "2026-05", "2026-06", "2026-07"]
    valores = [10, 20, 30, 50]
    serie = {
        "meses": meses,
        "series": {"nicho-teste": {"pontos": dict(zip(meses, valores, strict=True))}},
    }
    previsao = {
        "avaliacoes": [
            {
                "niche_id": "nicho-teste",
                "status": "avaliado",
                "regime": "tendencia",
                "modelo_campeao": "holt",
                "backtest": {"holt": {"mae": 3.5}},
            }
        ],
    }
    serie_path = tmp_path / "serie.json"
    previsao_path = tmp_path / "previsao.json"
    historico_path = tmp_path / "historico.jsonl"
    serie_path.write_text(json.dumps(serie), encoding="utf-8")
    previsao_path.write_text(json.dumps(previsao), encoding="utf-8")
    monkeypatch.setattr(monitoramento, "SERIE", serie_path)
    monkeypatch.setattr(monitoramento, "PREVISAO", previsao_path)
    monkeypatch.setattr(monitoramento, "HISTORICO", historico_path)

    registro_novo = aferir()["novas"][0]
    esperado = float(METODOS["holt"](np.array(valores[:-1], dtype=float), 1)[0])

    assert registro_novo["modelo"] == "holt"
    assert registro_novo["previsto"] == esperado
    assert registro_novo["previsto"] != valores[-2]
    assert registro_novo["erro_absoluto"] == abs(valores[-1] - esperado)
    assert registro_novo["versao_metodologia_afericao"] == 2


# ------------------------------------------------------------ calendario
def test_mes_anterior_dentro_do_ano():
    assert mes_anterior("2026-07") == "2026-06"


def test_mes_anterior_atravessa_o_ano():
    assert mes_anterior("2026-01") == "2025-12"


@pytest.mark.parametrize("mes", ["2024-03", "2025-11", "2026-08"])
def test_mes_anterior_devolve_formato_valido(mes):
    a = mes_anterior(mes)
    ano, m = a.split("-")
    assert len(ano) == 4 and len(m) == 2 and 1 <= int(m) <= 12


# --------------------------------------------------------------- alertas
def test_um_registro_nao_gera_alerta():
    """Sem historico nao ha com o que comparar — alertar seria chute."""
    assert alertas([registro("tributario", "2026-07", 50)]) == []


def test_erro_dentro_do_padrao_nao_alerta():
    h = [registro("tributario", f"2026-0{m}", 10) for m in (4, 5, 6)]
    h.append(registro("tributario", "2026-07", 12))
    assert alertas(h) == []


def test_erro_muito_acima_do_historico_alerta():
    h = [registro("tributario", f"2026-0{m}", 10) for m in (4, 5, 6)]
    h.append(registro("tributario", "2026-07", 10 * FATOR_ALERTA + 5))
    saida = alertas(h)
    assert len(saida) == 1
    assert saida[0]["niche_id"] == "tributario"
    assert saida[0]["razao"] > FATOR_ALERTA


def test_alerta_compara_com_a_media_anterior_nao_inclui_o_proprio_mes():
    """Incluir o mes recente na media diluiria o desvio que se quer detectar."""
    h = [registro("x", "2026-05", 10), registro("x", "2026-06", 10), registro("x", "2026-07", 100)]
    saida = alertas(h)
    assert saida[0]["media_anterior"] == 10.0
    assert saida[0]["razao"] == 10.0


def test_alerta_usa_o_mes_mais_recente_mesmo_fora_de_ordem():
    h = [registro("x", "2026-07", 100), registro("x", "2026-05", 10), registro("x", "2026-06", 10)]
    saida = alertas(h)
    assert saida and saida[0]["mes"] == "2026-07"


def test_media_zero_nao_divide_por_zero():
    h = [registro("x", "2026-05", 0), registro("x", "2026-06", 0), registro("x", "2026-07", 5)]
    assert alertas(h) == []


def test_nichos_sao_avaliados_de_forma_independente():
    h = [
        registro("a", "2026-06", 10),
        registro("a", "2026-07", 100),
        registro("b", "2026-06", 10),
        registro("b", "2026-07", 11),
    ]
    saida = alertas(h)
    assert {s["niche_id"] for s in saida} == {"a"}


def test_alerta_explica_a_leitura():
    h = [registro("x", "2026-06", 10), registro("x", "2026-07", 100)]
    assert "regime" in alertas(h)[0]["leitura"]
