# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Modelo eleitoral — o que ele recusa, e o que ele confessa sobre si mesmo.

Dois grupos de teste importam aqui.

O primeiro trava as recusas: o modelo nunca inventa distribuição, nunca trata
ausência de dado como zero, nunca devolve número quando não tem sinal. Um modelo
preditivo que devolve algo em toda situação é indistinguível de um gerador de
números plausíveis.

O segundo trava as CONFISSÕES, e é a parte incomum. ``avisos()`` existe para que
o modelo denuncie a própria obsolescência — calibração vencida, viés conhecido,
família única de sinal. É a regra permanente do titular virando comportamento
verificável: *"o mundo muda, os algoritmos mudam; o motor tem que ser dinâmico"*.
Sem teste, esse aviso é a primeira coisa que alguém apaga para "limpar a saída".
"""

from __future__ import annotations

from datetime import date

import pytest

from asus_theye.markets.modelo_eleitoral import (
    Modelo,
    ModeloError,
    Sinal,
    brier,
    clr,
    de_clr,
    erro_absoluto_medio,
    normalizar,
)

HOJE = date(2026, 8, 30)


def sinal_atencao(**troca) -> Sinal:
    base = dict(
        nome="atencao",
        valores={"LULA": 0.35, "BOLSONARO": 0.30, "CIRO": 0.25, "TEBET": 0.10},
        inclinacao=8.5,
        peso=1.0,
        calibrado_em=date(2022, 10, 1),
        calibrado_contra="TSE ele2022 1º turno",
    )
    base.update(troca)
    return Sinal(**base)


# --------------------------------------------------------------------------
# A geometria composicional


def test_log_razao_fecha_o_ciclo_de_ida_e_volta():
    """Ir e voltar tem de devolver a mesma composição."""
    c = {"A": 0.5, "B": 0.3, "C": 0.2}
    assert de_clr(clr(c)) == pytest.approx(c)


def test_a_volta_sempre_soma_um():
    assert sum(de_clr({"A": 4.0, "B": -1.0, "C": 0.5}).values()) == pytest.approx(1.0)


def test_inclinacao_alta_nao_estoura_a_exponencial():
    """O defeito que ``de_clr`` previne subtraindo o máximo.

    Com inclinação ~8 e coordenada ~5, ``exp(40)`` já é enorme; algumas
    combinações estouram para infinito e a composição vira NaN em silêncio —
    número inválido com aparência de número.
    """
    coords = {k: 8.5 * v for k, v in clr({"A": 0.97, "B": 0.02, "C": 0.01}).items()}
    fatias = de_clr(coords)
    assert sum(fatias.values()) == pytest.approx(1.0)
    assert all(0.0 <= v <= 1.0 for v in fatias.values())


def test_fatia_zerada_e_ausencia_de_sinal_nao_impossibilidade():
    """Zero não elimina candidato do páreo — só diz que não houve sinal."""
    fatias = de_clr(clr({"A": 0.6, "B": 0.4, "C": 0.0}))
    assert fatias["C"] > 0.0
    assert fatias["C"] < 1e-3


def test_soma_zero_e_indisponibilidade_nao_empate():
    with pytest.raises(ModeloError, match="não positiva"):
        normalizar({"A": 0.0, "B": 0.0})


def test_composicao_negativa_e_recusada():
    with pytest.raises(ModeloError, match="negativo"):
        clr({"A": 0.5, "B": -0.2})


# --------------------------------------------------------------------------
# As recusas do modelo


def test_sem_sinal_o_modelo_nao_inventa_distribuicao():
    m = Modelo(candidatos=("A", "B"))
    with pytest.raises(ModeloError, match="nenhum sinal"):
        m.fatias()


def test_todos_os_pesos_zerados_tambem_recusa():
    m = Modelo(candidatos=("A", "B"), sinais=[Sinal("x", {"A": 1, "B": 1}, peso=0.0)])
    with pytest.raises(ModeloError, match="peso zero"):
        m.fatias()


def test_sinal_que_nao_cobre_um_candidato_levanta():
    """Ausência nunca vira zero: zero afirmaria que o candidato não tem nada."""
    m = Modelo(candidatos=("A", "B", "C"), sinais=[Sinal("x", {"A": 1, "B": 1})])
    with pytest.raises(ModeloError, match="não cobre"):
        m.fatias()


def test_disputa_precisa_de_dois_candidatos():
    with pytest.raises(ModeloError, match="dois candidatos"):
        Modelo(candidatos=("A",))


def test_candidato_repetido_e_recusado():
    with pytest.raises(ModeloError, match="repetido"):
        Modelo(candidatos=("A", "B", "A"))


@pytest.mark.parametrize("ruim", [{"peso": -1.0}, {"inclinacao": 0.0}, {"inclinacao": -2.0}])
def test_parametros_impossiveis_sao_recusados_na_construcao(ruim):
    with pytest.raises(ModeloError):
        sinal_atencao(**ruim)


# --------------------------------------------------------------------------
# As confissões — o motor dinâmico virando comportamento


def test_calibracao_vencida_se_denuncia_sozinha():
    """A regra permanente do titular, em forma verificável."""
    m = Modelo(candidatos=("LULA", "BOLSONARO", "CIRO", "TEBET"), sinais=[sinal_atencao()])
    avisos = " ".join(m.avisos(HOJE))
    assert "vencido" in avisos
    assert "TSE ele2022" in avisos


def test_sinal_nunca_calibrado_e_denunciado():
    m = Modelo(candidatos=("A", "B"), sinais=[Sinal("cru", {"A": 1, "B": 2})])
    assert any("nunca calibrado" in a for a in m.avisos(HOJE))


def test_familia_unica_de_sinal_e_denunciada_com_o_motivo_medido():
    """O aviso cita o erro real do backtest, não uma preocupação genérica."""
    m = Modelo(candidatos=("LULA", "BOLSONARO", "CIRO", "TEBET"), sinais=[sinal_atencao()])
    avisos = " ".join(m.avisos(HOJE))
    assert "Ciro Gomes" in avisos and "8,36" in avisos


def test_vies_declarado_aparece_no_relatorio():
    """Viés que fica só no comentário do código não protege ninguém."""
    m = Modelo(
        candidatos=("A", "B"),
        sinais=[sinal_atencao(valores={"A": 1, "B": 2},
                              vies_declarado="leitorado da Wikipédia é jovem e urbano")],
    )
    assert any("jovem e urbano" in a for a in m.avisos(HOJE))


def test_duas_familias_recentes_nao_geram_aviso():
    """Quando está tudo em ordem, o relatório fica vazio — o aviso significa algo."""
    recente = date(2026, 7, 1)
    m = Modelo(
        candidatos=("A", "B"),
        sinais=[
            Sinal("um", {"A": 2, "B": 1}, calibrado_em=recente, calibrado_contra="x"),
            Sinal("dois", {"A": 1, "B": 3}, calibrado_em=recente, calibrado_contra="y"),
        ],
    )
    assert m.avisos(HOJE) == []


# --------------------------------------------------------------------------
# A combinação e a leitura


def test_duas_familias_puxam_o_resultado_para_o_meio():
    """É o ponto da combinação: nenhuma família decide sozinha."""
    so_um = Modelo(candidatos=("A", "B"), sinais=[Sinal("um", {"A": 0.9, "B": 0.1})]).fatias()
    com_dois = Modelo(
        candidatos=("A", "B"),
        sinais=[Sinal("um", {"A": 0.9, "B": 0.1}), Sinal("dois", {"A": 0.1, "B": 0.9})],
    ).fatias()
    assert so_um["A"] > com_dois["A"] > 0.4


def test_peso_zero_desliga_a_familia_sem_apaga_la_do_registro():
    m = Modelo(
        candidatos=("A", "B"),
        sinais=[Sinal("vale", {"A": 0.9, "B": 0.1}), Sinal("ignorada", {"A": 0.1, "B": 0.9}, peso=0.0)],
    )
    assert m.fatias()["A"] > 0.8
    assert any("desligado" in a for a in m.avisos(HOJE))


def test_maioria_absoluta_decide_o_segundo_turno():
    """Art. 77 §3º: eleito em 1º turno quem tem MAIS da metade dos válidos."""
    folgado = Modelo(candidatos=("A", "B"), sinais=[Sinal("s", {"A": 0.9, "B": 0.1}, inclinacao=3)])
    assert folgado.probabilidade_de_segundo_turno() == 0.0
    apertado = Modelo(candidatos=("A", "B"), sinais=[Sinal("s", {"A": 0.5, "B": 0.5})])
    assert apertado.probabilidade_de_segundo_turno() == 1.0


def test_ordem_e_a_saida_em_que_se_confia_mais():
    """O backtest mostrou o sinal bom para ordenar e ruim para dimensionar."""
    m = Modelo(candidatos=("A", "B", "C"), sinais=[Sinal("s", {"A": 0.5, "B": 0.3, "C": 0.2})])
    assert [n for n, _ in m.ordem()] == ["A", "B", "C"]


# --------------------------------------------------------------------------
# A régua


def test_brier_do_acaso_entre_dois_lados_e_um_quarto():
    """O número que define se um modelo vale alguma coisa."""
    assert brier({"A": 0.5, "B": 0.5}, {"A": True, "B": False}) == pytest.approx(0.25)


def test_previsao_certa_e_confiante_zera_o_brier():
    assert brier({"A": 1.0, "B": 0.0}, {"A": True, "B": False}) == pytest.approx(0.0)


def test_amortecer_probabilidade_piora_o_brier():
    """A prova de que hedge não é segurança — é erro transferido para a régua.

    Empurrar o número para 50% "para não errar feio" não reduz erro nenhum:
    move o erro para o Brier, que é justamente o ativo que se vende.
    """
    confiante = brier({"A": 0.9, "B": 0.1}, {"A": True, "B": False})
    amortecido = brier({"A": 0.6, "B": 0.4}, {"A": True, "B": False})
    assert amortecido > confiante


def test_brier_exige_desfecho_de_todo_mundo():
    with pytest.raises(ModeloError, match="sem desfecho"):
        brier({"A": 0.5, "B": 0.5}, {"A": True})


def test_erro_medio_reproduz_o_numero_do_backtest():
    """Confere a métrica contra valores reais do 1º turno de 2022."""
    previsto = {"LULA": 0.4907, "BOLSONARO": 0.3827, "CIRO": 0.1141, "TEBET": 0.0087}
    real = {"LULA": 0.4872, "BOLSONARO": 0.4346, "CIRO": 0.0306, "TEBET": 0.0419}
    assert erro_absoluto_medio(previsto, real) == pytest.approx(4.30, abs=0.05)


def test_erro_medio_sem_candidato_em_comum_levanta():
    with pytest.raises(ModeloError, match="em comum"):
        erro_absoluto_medio({"A": 0.5}, {"B": 0.5})
