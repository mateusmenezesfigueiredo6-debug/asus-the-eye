# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conformal adaptativo — a promessa, o limite da promessa, e o alarme.

Três coisas precisam ficar travadas aqui.

**A direção da realimentação.** Errou, aperta; acertou, afrouxa. Trocar o sinal
dessa conta produziria um sistema que reage ao contrário — alargando a faixa
justamente quando está indo bem — e nada no resultado pareceria errado à primeira
vista, porque as faixas continuariam sendo produzidas.

**O alarme.** É o que transforma um número solto (``alpha = 0,03``) em
informação acionável. Sem teste, é a primeira coisa que alguém remove para
"limpar a saída", e o motor volta a envelhecer em silêncio.

**O que NÃO se promete.** Adaptação corrige calibração, nunca acurácia. Um
modelo errado sobre um candidato ganha faixa larga, não faixa certa. Confundir as
duas coisas seria vender o mecanismo como se fosse inteligência.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.conformal import ConformalError
from asus_theye.markets.conformal_adaptativo import Adaptador, simular_deriva


# --------------------------------------------------------------------------
# A direção da realimentação


def test_errar_aperta_o_alpha_e_alarga_a_proxima_faixa():
    a = Adaptador(alpha_alvo=0.10, gamma=0.05)
    depois = a.observar(caiu_dentro=False)
    assert depois < 0.10


def test_acertar_afrouxa_um_pouco():
    a = Adaptador(alpha_alvo=0.10, gamma=0.05)
    assert a.observar(caiu_dentro=True) > 0.10


def test_o_passo_do_erro_e_muito_maior_que_o_do_acerto():
    """É o que faz o sistema reagir rápido a problema e devagar a sucesso.

    Com alvo 0,10: acertar move +gamma*0,10; errar move -gamma*0,90. Nove vezes
    mais forte na direção de proteger. Assimetria proposital.
    """
    erro = Adaptador(alpha_alvo=0.10, gamma=0.05)
    acerto = Adaptador(alpha_alvo=0.10, gamma=0.05)
    d_erro = abs(erro.observar(False) - 0.10)
    d_acerto = abs(acerto.observar(True) - 0.10)
    assert d_erro == pytest.approx(9 * d_acerto, rel=1e-6)


def test_uma_sequencia_perfeita_estabiliza_perto_do_alvo():
    """Acertar sempre não faz o alpha explodir — ele é preso abaixo de 1."""
    a = Adaptador(alpha_alvo=0.10, gamma=0.05)
    for _ in range(500):
        a.observar(True)
    assert a.alpha_corrente < 1.0


def test_errar_sempre_nao_faz_o_alpha_ficar_negativo():
    """Alpha negativo produziria faixa infinita sem lançar erro nenhum."""
    a = Adaptador(alpha_alvo=0.10, gamma=0.05)
    for _ in range(500):
        a.observar(False)
    assert a.alpha_corrente > 0.0


# --------------------------------------------------------------------------
# O alarme de calibração vencida


def test_modelo_que_passou_a_errar_dispara_o_alerta():
    """O caso que o mecanismo existe para pegar."""
    a = Adaptador(alpha_alvo=0.10, gamma=0.05)
    for _ in range(30):
        a.observar(False)
    d = a.diagnostico()
    assert "ALERTA" in d
    assert "calibração vencida" in d
    assert "reestime" in d


def test_modelo_saudavel_nao_dispara_alerta():
    """Alarme que toca sempre é alarme que se aprende a ignorar."""
    a = Adaptador(alpha_alvo=0.10, gamma=0.05)
    for i in range(30):
        a.observar(i % 10 != 0)  # 90% de acerto, exatamente o alvo
    assert "ALERTA" not in a.diagnostico()


def test_faixa_conservadora_demais_tambem_e_sinalizada():
    """Faixa que sempre acerta por ser larga não informa nada.

    O outro lado do erro, e menos óbvio: cobertura acima do alvo parece bom e
    significa que a previsão perdeu utilidade.
    """
    a = Adaptador(alpha_alvo=0.02, gamma=0.05)
    for _ in range(40):
        a.observar(True)
    assert "conservador em excesso" in a.diagnostico()


def test_historico_curto_e_declarado_como_insuficiente():
    a = Adaptador(alpha_alvo=0.10)
    a.observar(True)
    assert "histórico curto" in a.diagnostico()


def test_sem_resultado_nao_ha_diagnostico_inventado():
    assert "nada a diagnosticar" in Adaptador().diagnostico()
    assert Adaptador().cobertura_observada is None


# --------------------------------------------------------------------------
# Quando confiar na faixa


def test_nao_e_estavel_antes_de_ter_historico():
    """Antes do mínimo, o adaptador está aprendendo — dizer o contrário seria
    vender aprendizado como garantia."""
    a = Adaptador(alpha_alvo=0.10)
    for _ in range(5):
        a.observar(True)
    assert a.estavel() is False


def test_e_estavel_quando_a_cobertura_bate_o_alvo_com_historico():
    a = Adaptador(alpha_alvo=0.10, gamma=0.05)
    for i in range(50):
        a.observar(i % 10 != 0)
    assert a.estavel() is True


def test_nao_e_estavel_quando_a_cobertura_esta_longe_do_alvo():
    a = Adaptador(alpha_alvo=0.10, gamma=0.05)
    for i in range(50):
        a.observar(i % 2 == 0)  # 50% de cobertura, alvo era 90%
    assert a.estavel() is False


# --------------------------------------------------------------------------
# A demonstração de deriva e os parâmetros


def test_mudanca_de_regime_faz_o_alpha_desabar():
    """A pergunta do titular respondida com número: o motor percebe?"""
    estavel = [0.01] * 40
    ruim = [0.50] * 40
    a, r = simular_deriva(estavel, ruim, alpha_alvo=0.10, gamma=0.05)
    assert r["alpha_final"] < r["alpha_na_virada"]
    assert "ALERTA" in a.diagnostico()


def test_a_trilha_de_alpha_fica_registrada_para_auditoria():
    a = Adaptador(alpha_alvo=0.10)
    for _ in range(5):
        a.observar(True)
    assert len(a.trilha_alpha) == 6  # o inicial mais um por observação


@pytest.mark.parametrize("ruim", [{"alpha_alvo": 0.0}, {"alpha_alvo": 1.0}, {"gamma": 0.0}, {"gamma": 1.5}])
def test_parametros_impossiveis_sao_recusados(ruim):
    with pytest.raises(ConformalError):
        Adaptador(**ruim)


def test_simulacao_exige_as_duas_fases():
    with pytest.raises(ConformalError, match="ambas as fases"):
        simular_deriva([0.1], [])
