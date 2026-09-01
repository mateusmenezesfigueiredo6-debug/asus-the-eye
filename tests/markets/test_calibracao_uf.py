# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Calibração por UF — travando a distinção entre resíduo de geografia e de ciclo.

O ponto central: estes resíduos vêm de 2022 e SEMPRE produzem faixa marcada
como indicativa. Se um teste algum dia passar com ``garantia_valida=True`` para
uma faixa vinda deste módulo, alguém removeu ``permutavel=False`` — e essa é
exatamente a mentira que a trava do backtest existe para impedir.
"""

from __future__ import annotations

import json

import pytest

from asus_theye.markets.calibracao_uf import (
    CalibracaoUFError,
    faixas_indicativas,
    residuos_nacional_para_uf,
)
from asus_theye.markets.modelo_2026 import Evidencia, Modelo2026

DADOS = {
    "sp": {"cand": {"A": {"pvap": 60.0, "vap": 600}, "B": {"pvap": 40.0, "vap": 400}}},
    "rj": {"cand": {"A": {"pvap": 45.0, "vap": 450}, "B": {"pvap": 55.0, "vap": 550}}},
    "mg": {"cand": {"A": {"pvap": 55.0, "vap": 550}, "B": {"pvap": 45.0, "vap": 450}}},
}


def test_conta_297_pontos_do_arquivo_real(tmp_path):
    """A prova de que o cabo está ligado na fonte real, não só no mock."""
    dados = json.loads((__import__("pathlib").Path("dados/uf2022_tse.json")).read_text())
    residuos = residuos_nacional_para_uf(dados)
    assert len(residuos) == 297


def test_residuo_e_fracao_nao_percentual():
    """0,2637, não 26,37 — mesma armadilha de escala que a varredura achou
    entre fonte_tse (0-100) e modelo_eleitoral (0-1)."""
    residuos = residuos_nacional_para_uf(DADOS)
    assert all(0 <= r <= 1 for r in residuos)


def test_erro_zero_quando_estado_replica_a_media_nacional():
    """UF cujo resultado é idêntico à média nacional tem resíduo zero."""
    identico = {
        "a": {"cand": {"X": {"pvap": 50.0, "vap": 500}, "Y": {"pvap": 50.0, "vap": 500}}},
        "b": {"cand": {"X": {"pvap": 50.0, "vap": 500}, "Y": {"pvap": 50.0, "vap": 500}}},
    }
    assert max(residuos_nacional_para_uf(identico)) == pytest.approx(0.0)


def test_candidato_so_em_uma_uf_nao_quebra_a_conta():
    """Candidato regional não derruba o cálculo — só não compõe a fatia nacional
    de quem não o tem."""
    dados = dict(DADOS)
    dados["ac"] = {"cand": {"A": {"pvap": 70.0, "vap": 70}, "C": {"pvap": 30.0, "vap": 30}}}
    residuos = residuos_nacional_para_uf(dados)
    assert len(residuos) == 8  # 3 UFs x 2 candidatos + AC (A conta, C não tem par nacional)


# --------------------------------------------------------------------------
# A trava central: faixa sempre indicativa, nunca garantida


def test_faixa_de_calibracao_de_uf_e_sempre_indicativa():
    """Se isto passar com garantia_valida=True, alguém removeu permutavel=False."""
    m = Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=0,
                    evidencias=[Evidencia("x", {"A": 0.6, "B": 0.4}, peso=1.0, fonte_do_peso="y")])
    residuos = residuos_nacional_para_uf(DADOS)
    faixas = faixas_indicativas(m, residuos)
    assert all(not i.garantia_valida for i in faixas.values())
    assert all("INDICATIVO" in str(i) for i in faixas.values())


def test_faixa_centra_na_ordem_nao_na_magnitude_encolhida():
    """As faixas usam fatias(magnitude=False) — a ordem que a evidência
    sustenta hoje, não a distribuição uniforme do encolhimento total."""
    m = Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=0,
                    evidencias=[Evidencia("x", {"A": 0.7, "B": 0.3}, peso=1.0, fonte_do_peso="y")])
    residuos = residuos_nacional_para_uf(DADOS)
    faixas = faixas_indicativas(m, residuos)
    assert faixas["A"].centro > faixas["B"].centro


def test_cobertura_com_297_pontos_alcanca_95_por_cento():
    """A conta que motivou o módulo: com n=7 o teto era 87,5%; com 297, 95%
    vira alcançável de verdade."""
    dados = json.loads((__import__("pathlib").Path("dados/uf2022_tse.json")).read_text())
    residuos = residuos_nacional_para_uf(dados)
    m = Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=0,
                    evidencias=[Evidencia("x", {"A": 0.6, "B": 0.4}, peso=1.0, fonte_do_peso="y")])
    i = faixas_indicativas(m, residuos, alpha=0.05)["A"]
    assert i.cobertura_garantida >= 0.95


# --------------------------------------------------------------------------
# As recusas


def test_uf_sem_candidatos_em_formato_valido_e_recusada():
    with pytest.raises(CalibracaoUFError, match="candidatos"):
        residuos_nacional_para_uf({"sp": {"cand": "não é um dict"}})


def test_vap_ausente_e_recusado():
    with pytest.raises(CalibracaoUFError, match="vap"):
        residuos_nacional_para_uf({"sp": {"cand": {"A": {"pvap": 50.0}}}})


def test_arquivo_inexistente_e_recusado():
    from asus_theye.markets.calibracao_uf import carregar_uf2022
    with pytest.raises(CalibracaoUFError, match="não encontrada"):
        carregar_uf2022("/caminho/que/nao/existe.json")
