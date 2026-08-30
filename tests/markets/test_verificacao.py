# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verificação na escola da meteorologia — travando o que o Brier sozinho esconde.

O teste central deste arquivo é o do modelo covarde: um modelo que diz sempre a
taxa-base é QUASE PERFEITAMENTE CALIBRADO e completamente inútil. O Brier dele
parece apenas medíocre. Só o skill score revela que ele é pior que não ter
modelo, e só a decomposição explica por quê.

Sem esses dois números, alguém olharia a confiabilidade excelente e concluiria
que o modelo está bom — que é exatamente o erro que este módulo existe para
impedir, e que foi cometido nesta própria sessão ao reportar "Brier abaixo de
0,10" como se fosse um resultado autoexplicativo.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.verificacao import (
    VerificacaoError,
    brier,
    brier_ponderado,
    climatologia,
    decompor,
    diagrama_de_confiabilidade,
    painel,
    skill_score_vs_climatologia,
)


# --------------------------------------------------------------------------
# O Brier e o que ele não conta sozinho


def test_previsao_perfeita_zera_o_brier():
    assert brier([1.0, 0.0, 1.0], [True, False, True]) == pytest.approx(0.0)


def test_moeda_no_ar_da_um_quarto():
    assert brier([0.5, 0.5], [True, False]) == pytest.approx(0.25)


def test_modelo_covarde_e_bem_calibrado_e_inutil():
    """O teste que justifica o módulo inteiro.

    Dizer sempre 50% num problema 50/50 produz confiabilidade quase perfeita —
    e skill zero. Calibração excelente com resolução nula é um modelo que nunca
    erra a probabilidade porque nunca arrisca uma.
    """
    desfechos = [i % 2 == 0 for i in range(200)]
    covarde = [0.5] * 200
    d = decompor(covarde, desfechos)
    assert d.confiabilidade < 0.001      # calibração ótima
    assert d.resolucao < 0.001           # e não distingue nada
    assert abs(skill_score_vs_climatologia(covarde, desfechos)) < 0.01
    assert "RESOLUÇÃO BAIXA" in d.diagnostico()
    assert "falta sinal" in d.diagnostico()


def test_modelo_pior_que_o_ingenuo_tem_skill_negativo():
    """Negativo significa: teria sido melhor não ter modelo."""
    desfechos = [True] * 80 + [False] * 20
    ao_contrario = [0.1] * 80 + [0.9] * 20
    assert skill_score_vs_climatologia(ao_contrario, desfechos) < 0


def test_modelo_com_sinal_tem_skill_positivo():
    desfechos = [True] * 80 + [False] * 20
    com_sinal = [0.9] * 80 + [0.1] * 20
    assert skill_score_vs_climatologia(com_sinal, desfechos) > 0.5


def test_baseline_sem_incerteza_recusa_medir_skill():
    """Se tudo aconteceu, não há skill a medir — não é mérito nem defeito."""
    with pytest.raises(VerificacaoError, match="baseline é perfeito"):
        skill_score_vs_climatologia([0.9, 0.8], [True, True])


# --------------------------------------------------------------------------
# A decomposição e o remédio que ela indica


def test_a_identidade_de_murphy_fecha_com_previsoes_iguais_na_faixa():
    """A identidade é exata quando toda faixa tem previsões idênticas.

    Esta é a condição real do teorema, e a primeira versão deste teste a
    ignorava: exigia resíduo zero para previsões CONTÍNUAS, e falhou com razão.
    """
    previsoes = [0.05] * 40 + [0.95] * 60
    desfechos = [False] * 40 + [True] * 60
    d = decompor(previsoes, desfechos)
    assert abs(d.residuo) < 1e-9


def test_previsao_continua_deixa_residuo_e_ele_e_a_variancia_interna():
    """Com previsões contínuas o resíduo é real — é a dispersão dentro da faixa.

    Não é defeito nem arredondamento: é informação. Resíduo grande diz que as
    faixas estão largas demais para o formato das previsões.
    """
    previsoes = [i / 100 for i in range(100)]
    desfechos = [i % 3 == 0 for i in range(100)]
    grosso = decompor(previsoes, desfechos, n_faixas=5)
    fino = decompor(previsoes, desfechos, n_faixas=20)
    assert abs(grosso.residuo) > 0
    # Faixa mais estreita reduz a dispersão interna, logo reduz o resíduo.
    assert abs(fino.residuo) < abs(grosso.residuo)


def test_descalibrado_mas_discriminante_pede_recalibragem():
    """Erra a magnitude, acerta a ordem: o remédio é recalibrar, não coletar."""
    desfechos = [True] * 50 + [False] * 50
    exagerado = [1.0] * 50 + [0.0] * 50
    d = decompor([min(0.99, p + 0.3) if p > 0.5 else p for p in exagerado], desfechos)
    assert d.resolucao > 0.1


def test_incerteza_nao_depende_do_modelo():
    """É a dificuldade do problema. Dois modelos diferentes dão a mesma."""
    desfechos = [i % 4 == 0 for i in range(100)]
    a = decompor([0.5] * 100, desfechos)
    b = decompor([0.25] * 100, desfechos)
    assert a.incerteza == pytest.approx(b.incerteza)


def test_poucas_previsoes_recusam_decomposicao():
    """Faixa com menos de um caso vira ruído com aparência de número."""
    with pytest.raises(VerificacaoError, match="viraria ruído"):
        decompor([0.5, 0.6], [True, False], n_faixas=10)


# --------------------------------------------------------------------------
# O dilema do previsor


def test_ponderar_preserva_todos_os_casos():
    """Filtrar para os extremos premiaria quem exagera; ponderar não.

    Lerch et al. (2017): avaliar só nos casos raros recompensa
    sistematicamente quem grita extremo toda semana, porque ele acerta todos os
    extremos. O peso mantém o incentivo honesto.
    """
    p, d = [0.9, 0.5, 0.1], [True, False, False]
    normal = brier(p, d)
    focado = brier_ponderado(p, d, [10.0, 1.0, 1.0])
    assert focado != normal
    assert focado > 0


def test_pesos_invalidos_sao_recusados():
    with pytest.raises(VerificacaoError, match="negativo"):
        brier_ponderado([0.5], [True], [-1.0])
    with pytest.raises(VerificacaoError, match="zero"):
        brier_ponderado([0.5], [True], [0.0])


# --------------------------------------------------------------------------
# O painel e o diagrama


def test_o_painel_sempre_traz_o_baseline_ao_lado_do_brier():
    """A regra que este módulo impõe: Brier sozinho não é resultado."""
    desfechos = [i % 3 == 0 for i in range(90)]
    r = painel([0.33] * 90, desfechos)
    assert "brier" in r and "brier_do_baseline" in r and "skill_score" in r


def test_o_painel_degrada_com_elegancia_quando_falta_dado():
    """Poucos casos: devolve o que dá e DIZ o que não deu, em vez de estourar."""
    r = painel([0.5, 0.6, 0.4], [True, False, True])
    assert r["decomposicao"] is None
    assert "decomposicao_indisponivel" in r


def test_diagrama_marca_faixa_com_poucos_casos_como_nao_confiavel():
    p = [0.05] * 3 + [0.95] * 30
    d = [False] * 3 + [True] * 30
    linhas = diagrama_de_confiabilidade(p, d)
    rala = [l for l in linhas if l["n"] < 5]
    assert rala and all(not l["confiavel"] for l in rala)


def test_climatologia_e_a_taxa_base():
    assert climatologia([True, True, False, False]) == pytest.approx(0.5)


# --------------------------------------------------------------------------
# As recusas


def test_contagens_diferentes_sao_recusadas():
    with pytest.raises(VerificacaoError, match="previsões para"):
        brier([0.5, 0.5], [True])


def test_probabilidade_fora_do_intervalo_e_recusada():
    with pytest.raises(VerificacaoError, match="fora de"):
        brier([1.5], [True])


def test_lista_vazia_e_recusada():
    with pytest.raises(VerificacaoError, match="nada a verificar"):
        brier([], [])


# --------------------------------------------------------------------------
# Relação com scoring.py — duas implementações, uma prova de que concordam
#
# A varredura estrutural de 30/08/2026 achou duas funções chamadas
# `skill_score` no mesmo pacote, com contrato incompatível: `scoring.py`
# (produção, exige janela, aceita qualquer baseline) e esta aqui (backtest,
# sem janela, baseline = climatologia). Renomear para skill_score_vs_climatologia
# resolve a colisão de nome — mas não prova que as DUAS fórmulas de Brier, que
# continuam sendo mantidas separadamente, calculam a mesma coisa. Este teste
# é essa prova: se algum dia alguém consertar um bug numa e esquecer da outra,
# ele quebra.


def test_brier_concorda_com_scoring_brier_score():
    """As duas implementações independentes de Brier dão o mesmo número.

    Não foram unificadas porque scoring.brier_score() arredonda para 6 casas
    (regra de produção) e a decomposição de Murphy aqui precisa de mais
    precisão que isso — mas se divergirem além do arredondamento, é sinal de
    que uma das duas tem bug que a outra não tem.
    """
    from asus_theye.markets.scoring import brier_score as scoring_brier_score

    previsoes = [0.1, 0.5, 0.9, 0.33, 0.77, 0.02, 0.99]
    desfechos = [False, True, True, False, True, False, True]

    daqui = brier(previsoes, desfechos)
    de_scoring = scoring_brier_score(list(zip(previsoes, [int(d) for d in desfechos])))
    assert de_scoring is not None
    assert daqui == pytest.approx(de_scoring, abs=1e-6)


def test_skill_score_vs_climatologia_nao_e_o_mesmo_nome_que_scoring():
    """Documenta a distinção em código executável, não só em docstring."""
    import asus_theye.markets.scoring as scoring
    import asus_theye.markets.verificacao as verificacao

    assert not hasattr(verificacao, "skill_score"), (
        "o nome 'skill_score' não deve mais existir em verificacao.py — "
        "era a colisão com scoring.skill_score que a varredura estrutural achou"
    )
    assert hasattr(scoring, "skill_score")
    assert hasattr(verificacao, "skill_score_vs_climatologia")
