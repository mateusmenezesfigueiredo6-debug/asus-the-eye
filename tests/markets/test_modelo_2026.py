# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Modelo2026 — travando a distinção entre "sem resultado" e "sem evidência".

Este arquivo nasceu de um defeito real, cometido nesta sessão: rodar o modelo
contra atenção e tempo de TV de hoje, sem nenhum resultado eleitoral de 2026,
devolveu os onze candidatos empatados em 9,09% — a ORDEM sumiu junto com a
magnitude. Atenção e tempo de TV são evidência viva; o que falta é resultado
apurado, e são coisas diferentes. `observacoes_do_ciclo=0` estava sendo tratado
como "não sei nada", quando o correto é "não tenho como calibrar a ESCALA".

Por isso `fatias(magnitude=False)` existe, e este arquivo prova que ela faz o
que promete: preserva ordem sem apurar o ciclo, e é isso que evidência viva
sustenta mesmo sem resultado.
"""

from __future__ import annotations

from datetime import date

import pytest

from asus_theye.markets.modelo_2026 import Evidencia, Modelo2026, ModeloError


def evidencia_atencao(**troca) -> Evidencia:
    base = dict(
        nome="atencao",
        valores={"A": 0.55, "B": 0.30, "C": 0.15},
        peso=1.0,
        fonte_do_peso="Yasseri & Bright 2016",
    )
    base.update(troca)
    return Evidencia(**base)


# --------------------------------------------------------------------------
# O defeito central: ordem apagada junto com magnitude


def test_sem_resultado_do_ciclo_a_ordem_sobrevive():
    """O teste que teria pego o bug antes de eu rodar contra dado real."""
    m = Modelo2026(candidatos=("A", "B", "C"), observacoes_do_ciclo=0,
                    evidencias=[evidencia_atencao()])
    assert [n for n, _ in m.ordem()] == ["A", "B", "C"]


def test_ordem_nao_depende_da_ordem_de_declaracao_dos_candidatos():
    """O bug real que passou pela varredura estrutural de 30/08/2026.

    ``ordem()`` chamava ``fatias()`` (magnitude=True, o padrão) em vez de
    ``fatias(magnitude=False)``. Com encolhimento total tudo fica empatado em
    uniforme, ``sorted()`` é estável, e o resultado vira a ordem da TUPLA — não
    a ordem que a evidência sustenta. Mesma evidência, tupla em ordem diferente,
    tinha de dar "vencedor" diferente antes da correção.
    """
    evidencia = evidencia_atencao(valores={"A": 0.55, "B": 0.30, "C": 0.15})
    direto = Modelo2026(candidatos=("A", "B", "C"), observacoes_do_ciclo=0,
                         evidencias=[evidencia])
    invertido = Modelo2026(candidatos=("C", "B", "A"), observacoes_do_ciclo=0,
                            evidencias=[evidencia])
    assert [n for n, _ in direto.ordem()] == [n for n, _ in invertido.ordem()] == ["A", "B", "C"]


def test_magnitude_true_encolhe_ate_ficar_uniforme_sem_resultado():
    """A magnitude precisa da trava; a ordem, não."""
    m = Modelo2026(candidatos=("A", "B", "C"), observacoes_do_ciclo=0,
                    evidencias=[evidencia_atencao()])
    fatias = m.fatias(magnitude=True)
    assert max(fatias.values()) - min(fatias.values()) < 1e-6


def test_magnitude_false_preserva_a_distancia_entre_candidatos():
    m = Modelo2026(candidatos=("A", "B", "C"), observacoes_do_ciclo=0,
                    evidencias=[evidencia_atencao()])
    fatias = m.fatias(magnitude=False)
    assert fatias["A"] > fatias["B"] > fatias["C"]


def test_com_calibracao_plena_magnitude_e_ordem_coincidem():
    m = Modelo2026(candidatos=("A", "B", "C"), observacoes_do_ciclo=19,
                    evidencias=[evidencia_atencao()])
    assert m.fatias(magnitude=True) == pytest.approx(m.fatias(magnitude=False))


# --------------------------------------------------------------------------
# O encolhimento em si


def test_encolhimento_cai_linearmente_com_observacoes():
    m = Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=0,
                    evidencias=[evidencia_atencao(valores={"A": 0.6, "B": 0.4})])
    assert m.encolhimento == 1.0
    m.observacoes_do_ciclo = 10
    assert m.encolhimento == pytest.approx(1 - 10 / 19)
    m.observacoes_do_ciclo = 19
    assert m.encolhimento == 0.0


def test_observacoes_alem_do_necessario_nao_produzem_encolhimento_negativo():
    m = Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=999,
                    evidencias=[evidencia_atencao(valores={"A": 0.6, "B": 0.4})])
    assert m.encolhimento == 0.0


def test_segundo_turno_e_none_com_encolhimento_alto():
    """Ignorância não vira previsão de 2º turno — nem sim, nem não."""
    m = Modelo2026(candidatos=("A", "B", "C"), observacoes_do_ciclo=0,
                    evidencias=[evidencia_atencao()])
    assert m.houve_segundo_turno() is None


def test_segundo_turno_responde_com_calibracao_suficiente():
    m = Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=19,
                    evidencias=[evidencia_atencao(valores={"A": 0.9, "B": 0.1})])
    assert m.houve_segundo_turno() is False  # maioria absoluta, sem 2º turno


# --------------------------------------------------------------------------
# Peso exige fonte — a trava contra reintroduzir sobreajuste


def test_peso_sem_fonte_e_recusado():
    with pytest.raises(ModeloError, match="sem fonte"):
        Evidencia(nome="x", valores={"A": 1}, peso=1.0, fonte_do_peso="")


def test_peso_nao_positivo_e_recusado():
    with pytest.raises(ModeloError, match="positivo"):
        Evidencia(nome="x", valores={"A": 1}, peso=0.0, fonte_do_peso="qualquer")


# --------------------------------------------------------------------------
# As recusas usuais


def test_sem_evidencia_nao_inventa_distribuicao():
    with pytest.raises(ModeloError, match="nenhuma evidência"):
        Modelo2026(candidatos=("A", "B")).fatias()


def test_evidencia_que_nao_cobre_candidato_levanta():
    m = Modelo2026(candidatos=("A", "B", "C"),
                    evidencias=[Evidencia("x", {"A": 1, "B": 1}, peso=1.0, fonte_do_peso="y")])
    with pytest.raises(ModeloError, match="não cobre"):
        m.fatias()


def test_menos_de_dois_candidatos_e_recusado():
    with pytest.raises(ModeloError, match="dois candidatos"):
        Modelo2026(candidatos=("A",))


def test_observacoes_negativas_sao_recusadas():
    with pytest.raises(ModeloError, match="negativa"):
        Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=-1)


# --------------------------------------------------------------------------
# Os avisos


def test_zero_observacoes_avisa_que_e_honestidade_nao_falha():
    m = Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=0,
                    evidencias=[evidencia_atencao(valores={"A": 0.6, "B": 0.4})])
    assert any("honestidade" in a for a in m.avisos())


def test_familia_unica_e_avisada():
    m = Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=19,
                    evidencias=[evidencia_atencao(valores={"A": 0.6, "B": 0.4})])
    assert any("família única" in a for a in m.avisos())


def test_peso_e_fonte_aparecem_no_relatorio():
    m = Modelo2026(candidatos=("A", "B"), observacoes_do_ciclo=19,
                    evidencias=[evidencia_atencao(valores={"A": 0.6, "B": 0.4},
                                fonte_do_peso="Zucco 2013, AJPS")])
    assert any("Zucco 2013" in a for a in m.avisos())


def test_residuos_para_conformal_vazio_ate_haver_resultado():
    m = Modelo2026(candidatos=("A", "B"), evidencias=[evidencia_atencao(valores={"A": 0.6, "B": 0.4})])
    assert m.residuos_para_conformal() == []
