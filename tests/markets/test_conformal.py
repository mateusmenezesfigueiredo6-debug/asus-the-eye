# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inferência conformal — com foco no que o módulo se RECUSA a fazer.

O caminho feliz de um intervalo conformal é aritmética simples. O que merece
teste é a honestidade: o módulo existe tanto para dar a faixa quanto para dizer
que a faixa pedida não pode ser honrada com os dados que existem.

A tentação que estes testes travam é específica e sedutora: pedir 95% de
cobertura, receber dois números, e publicá-los. Com sete pontos de calibração
esses dois números existem — só não valem 95%. Um intervalo com rótulo errado é
pior que nenhum intervalo, porque tem a forma da estatística e o conteúdo do
chute.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.conformal import (
    ConformalError,
    cobertura_efetiva,
    cobertura_observada,
    intervalo,
    pontos_necessarios,
)

#: Resíduos reais do backtest contra o 1º turno de 2022, em fração de voto.
#: São |previsto − real| de cada candidato, com o modelo de log-razão.
RESIDUOS_2022 = [0.0035, 0.0519, 0.0836, 0.0331, 0.0015, 0.0004, 0.0002]


# --------------------------------------------------------------------------
# A conta que decide se uma meta é alcançável hoje


@pytest.mark.parametrize(
    "alpha,esperado",
    [(0.05, 19), (0.10, 9), (0.20, 4), (0.50, 1)],
)
def test_quantos_pontos_uma_cobertura_exige(alpha, esperado):
    """Para 95% são 19 pontos. Temos 7. Isso é aritmética, não opinião."""
    assert pontos_necessarios(alpha) == esperado


def test_com_sete_pontos_noventa_e_cinco_por_cento_nao_existe():
    """O teste central deste arquivo.

    Sete candidatos de uma eleição dão granularidade de 1/8 = 12,5%. O teto é
    87,5%, e 95% não é atingível — não por limitação do modelo, mas por
    quantidade de eleições já ocorridas com dado utilizável.
    """
    assert cobertura_efetiva(7, 0.05) == pytest.approx(7 / 8)
    assert cobertura_efetiva(7, 0.05) < 0.95


def test_a_granularidade_e_grossa_e_isso_aparece():
    """Com n=7, pedir 95%, 90% ou 80% devolve a MESMA cobertura real.

    Não é bug: é o passo de 1/(n+1). Quem não souber disso acha que ajustou o
    rigor mudando o alpha, e não ajustou nada.
    """
    coberturas = {cobertura_efetiva(7, a) for a in (0.05, 0.10, 0.20)}
    assert len(coberturas) == 1


def test_com_calibracao_farta_a_cobertura_pedida_e_honrada():
    """Com dados suficientes a garantia é a pedida. O limite é o n, não o método."""
    assert cobertura_efetiva(99, 0.05) >= 0.95


# --------------------------------------------------------------------------
# O que o intervalo declara sobre si mesmo


def test_intervalo_avisa_quando_nao_pode_honrar_o_pedido():
    i = intervalo(0.35, RESIDUOS_2022, alpha=0.05)
    assert i.cobertura_garantida == pytest.approx(0.875)
    assert "19 pontos" in i.aviso
    assert i.alpha_pedido == 0.05  # guarda o que foi pedido, não o que entregou


def test_permutabilidade_violada_derruba_a_garantia_sem_derrubar_a_faixa():
    """Marca como indicativo em vez de recusar.

    A faixa continua informativa; o que não vale é o rótulo de cobertura. Recusar
    tudo empurraria quem usa para calcular à mão, sem aviso nenhum.
    """
    i = intervalo(0.35, RESIDUOS_2022, alpha=0.10, permutavel=False)
    assert i.garantia_valida is False
    assert "permutabilidade" in i.aviso.lower()
    assert i.largura > 0
    assert "INDICATIVO" in str(i)


def test_caso_permutavel_nao_carrega_o_aviso_de_garantia_quebrada():
    i = intervalo(0.35, RESIDUOS_2022, alpha=0.10, permutavel=True)
    assert i.garantia_valida is True
    assert "permutabilidade" not in i.aviso.lower()


def test_a_faixa_e_simetrica_e_contem_o_centro():
    i = intervalo(0.40, RESIDUOS_2022, alpha=0.10)
    assert i.baixo <= i.centro <= i.alto
    assert (i.centro - i.baixo) == pytest.approx(i.alto - i.centro)


def test_fatia_de_voto_nao_escapa_de_zero_a_um():
    """Faixa que passa de 100% ou desce de 0% seria absurdo aritmético."""
    i = intervalo(0.02, RESIDUOS_2022, alpha=0.10)
    assert i.baixo == 0.0
    j = intervalo(0.99, RESIDUOS_2022, alpha=0.10)
    assert j.alto == 1.0


# --------------------------------------------------------------------------
# As recusas


def test_sem_calibracao_nao_ha_intervalo():
    """Não existe faixa honesta sem histórico de erro."""
    with pytest.raises(ConformalError, match="sem resíduos"):
        intervalo(0.5, [], alpha=0.10)


def test_residuo_negativo_e_recusado():
    """Resíduo é erro ABSOLUTO. Negativo indica que quem chamou errou o sinal."""
    with pytest.raises(ConformalError, match="negativo"):
        intervalo(0.5, [0.01, -0.02], alpha=0.10)


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.5])
def test_alpha_fora_do_intervalo_aberto_e_recusado(alpha):
    with pytest.raises(ConformalError):
        cobertura_efetiva(7, alpha)


def test_calibracao_muito_curta_e_sinalizada():
    i = intervalo(0.5, [0.01, 0.02, 0.03], alpha=0.20)
    assert "instável" in i.aviso


# --------------------------------------------------------------------------
# A verificação empírica da garantia teórica


def test_cobertura_observada_confere_a_promessa():
    """A garantia é teórica; isto mede o que aconteceu de fato.

    Divergência grande entre garantida e observada é como se descobre que a
    permutabilidade quebrou — sem depender de alguém desconfiar.
    """
    faixas = [intervalo(0.5, RESIDUOS_2022, alpha=0.10) for _ in range(4)]
    assert cobertura_observada(faixas, [0.50, 0.52, 0.48, 0.99]) == pytest.approx(0.75)


def test_cobertura_observada_recusa_contagens_desiguais():
    faixas = [intervalo(0.5, RESIDUOS_2022, alpha=0.10)]
    with pytest.raises(ConformalError, match="intervalos para"):
        cobertura_observada(faixas, [0.5, 0.6])


def test_o_quantil_usa_o_ajuste_de_amostra_finita():
    """Guarda contra a troca silenciosa por percentil comum.

    Com n=7 e alpha=0.10, ceil(8 * 0.9) = 8 > 7, então o quantil cai no MAIOR
    resíduo. Um percentil comum devolveria algo menor, a faixa ficaria estreita
    demais, nenhum teste quebraria — e a garantia teria sumido em silêncio.
    """
    i = intervalo(0.5, RESIDUOS_2022, alpha=0.10)
    assert (i.alto - i.centro) == pytest.approx(max(RESIDUOS_2022))
