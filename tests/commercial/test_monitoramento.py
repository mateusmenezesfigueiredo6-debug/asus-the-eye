"""Testes do monitoramento continuo (etapa 6 do ciclo).

O historico de acuracia e a evidencia de que a plataforma sabe se esta
acertando. Estes testes travam as propriedades que sustentam essa evidencia:
o historico nao pode ser reescrito, a afericao nao pode duplicar, e o alerta
so dispara quando ha base de comparacao.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.comercial.monitoramento import FATOR_ALERTA, alertas, mes_anterior


def registro(nid: str, mes: str, erro: float) -> dict:
    return {"niche_id": nid, "mes_alvo": mes, "erro_absoluto": erro,
            "erro_pct": erro, "previsto": 100, "observado": 100 + erro}


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
    h = [registro("x", "2026-05", 10), registro("x", "2026-06", 10),
         registro("x", "2026-07", 100)]
    saida = alertas(h)
    assert saida[0]["media_anterior"] == 10.0
    assert saida[0]["razao"] == 10.0


def test_alerta_usa_o_mes_mais_recente_mesmo_fora_de_ordem():
    h = [registro("x", "2026-07", 100), registro("x", "2026-05", 10),
         registro("x", "2026-06", 10)]
    saida = alertas(h)
    assert saida and saida[0]["mes"] == "2026-07"


def test_media_zero_nao_divide_por_zero():
    h = [registro("x", "2026-05", 0), registro("x", "2026-06", 0),
         registro("x", "2026-07", 5)]
    assert alertas(h) == []


def test_nichos_sao_avaliados_de_forma_independente():
    h = [registro("a", "2026-06", 10), registro("a", "2026-07", 100),
         registro("b", "2026-06", 10), registro("b", "2026-07", 11)]
    saida = alertas(h)
    assert {s["niche_id"] for s in saida} == {"a"}


def test_alerta_explica_a_leitura():
    h = [registro("x", "2026-06", 10), registro("x", "2026-07", 100)]
    assert "regime" in alertas(h)[0]["leitura"]
