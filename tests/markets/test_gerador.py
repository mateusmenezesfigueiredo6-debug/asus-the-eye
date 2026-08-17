"""Testes do gerador WPAM.

Os vetores conhecidos reproduzem os exemplos publicados do SocialPredict
(Prediction_Market_Math, MIT) — prova de fidelidade à matemática, com código
independente. Ver reports/provenance/SocialPredict-WPAM.md.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.gerador import (
    PRIOR_NEUTRO,
    GeradorError,
    Sinal,
    gerar_probabilidade,
)


def sim(peso: float, fonte: str = "f") -> Sinal:
    return Sinal(direcao="sim", peso=peso, fonte=fonte)


def nao(peso: float, fonte: str = "f") -> Sinal:
    return Sinal(direcao="nao", peso=peso, fonte=fonte)


# --------------------------------------------------------- doutrina preservada


def test_sem_sinal_fica_no_prior_e_marca_maxima_incerteza() -> None:
    p = gerar_probabilidade([])
    assert p.valor == pytest.approx(0.5)
    assert p.max_uncertainty is True
    assert p.peso_sim == 0 and p.peso_nao == 0
    assert p.fontes == []


def test_prior_diferente_sem_sinal_devolve_o_prior() -> None:
    p = gerar_probabilidade([], p_inicial=0.3)
    assert p.valor == pytest.approx(0.3)
    assert p.max_uncertainty is False  # 0.3 não é o limiar


# --------------------------------------------------------- vetores do SocialPredict
# P = (0.5*I + A_sim) / (I + A_sim + A_nao)


@pytest.mark.parametrize(
    "peso_inicial,psim,pnao,esperado",
    [
        (10, 0, 20, 5 / 30),  # 0.5*10+0 / (10+0+20) = 0.167
        (10, 10, 20, 15 / 40),  # = 0.375
        (10, 20, 20, 25 / 50),  # = 0.5
    ],
)
def test_vetores_publicados(peso_inicial: float, psim: float, pnao: float, esperado: float) -> None:
    sinais = ([sim(psim)] if psim else []) + ([nao(pnao)] if pnao else [])
    p = gerar_probabilidade(sinais, peso_inicial=peso_inicial)
    assert p.valor == pytest.approx(esperado, abs=1e-6)


def test_evidencia_move_do_050() -> None:
    """A correção da falha: com sinal real, a probabilidade sai de 0,50."""
    forte_sim = gerar_probabilidade([sim(30, "BCB-nowcast")], peso_inicial=10)
    assert forte_sim.valor > 0.5 and forte_sim.max_uncertainty is False
    forte_nao = gerar_probabilidade([nao(30, "BCB-nowcast")], peso_inicial=10)
    assert forte_nao.valor < 0.5


def test_prior_mais_pesado_move_menos() -> None:
    leve = gerar_probabilidade([sim(10)], peso_inicial=5)
    pesado = gerar_probabilidade([sim(10)], peso_inicial=50)
    assert leve.valor > pesado.valor  # prior mais pesado resiste mais


def test_fontes_sao_agregadas_e_unicas() -> None:
    p = gerar_probabilidade([sim(5, "A"), sim(3, "B"), nao(2, "A")])
    assert p.fontes == ["A", "B"]
    assert p.valor == pytest.approx((0.5 * 10 + 8) / (10 + 8 + 2))


def test_resultado_sempre_em_0_1() -> None:
    assert 0.0 <= gerar_probabilidade([sim(1e6, "x")]).valor <= 1.0
    assert 0.0 <= gerar_probabilidade([nao(1e6, "x")]).valor <= 1.0


# --------------------------------------------------------- guardas (nunca palpite)


def test_sinal_sem_fonte_levanta() -> None:
    with pytest.raises(GeradorError, match="fonte"):
        gerar_probabilidade([Sinal(direcao="sim", peso=5, fonte="")])


@pytest.mark.parametrize("mau", [Sinal("talvez", 5, "f"), Sinal("sim", 0, "f"), Sinal("sim", -1, "f")])
def test_sinal_invalido_levanta(mau: Sinal) -> None:
    with pytest.raises(GeradorError):
        gerar_probabilidade([mau])


@pytest.mark.parametrize("mau", [-0.1, 1.5, True])
def test_prior_invalido_levanta(mau: object) -> None:
    with pytest.raises(GeradorError, match="p_inicial"):
        gerar_probabilidade([], p_inicial=mau)  # type: ignore[arg-type]


def test_peso_inicial_nao_positivo_levanta() -> None:
    with pytest.raises(GeradorError, match="peso_inicial"):
        gerar_probabilidade([], peso_inicial=0)


def test_prior_neutro_e_meio() -> None:
    assert PRIOR_NEUTRO == 0.5
