"""Testes do benchmark Max-Cut (QAOA vs ótimo exato)."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from asus_theye.benchmark.maxcut import (  # noqa: E402
    MaxCutError,
    MaxCutProblem,
    benchmark_maxcut,
    grafo_3_regular,
    otimo_forca_bruta,
    qaoa_maxcut,
)

# Triângulo: ótimo de corte = 2 (qualquer 1-vs-2 corta 2 das 3 arestas).
TRIANGULO = MaxCutProblem(name="tri", n_nodes=3, edges=((0, 1, 1.0), (1, 2, 1.0), (0, 2, 1.0)), seed=1)
# Quadrado (ciclo de 4): ótimo = 4 (bipartido, corta tudo).
QUADRADO = MaxCutProblem(name="quad", n_nodes=4, edges=((0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0), (0, 3, 1.0)), seed=1)


# --------------------------------------------------------------- problema


def test_cut_conta_arestas_cruzadas() -> None:
    assert TRIANGULO.cut((0, 1, 0)) == 2.0  # aresta (0,1) e (1,2) cortadas
    assert TRIANGULO.cut((0, 0, 0)) == 0.0  # nada cortado


def test_otimo_forca_bruta_conhecido() -> None:
    assert otimo_forca_bruta(TRIANGULO)[1] == 2.0
    assert otimo_forca_bruta(QUADRADO)[1] == 4.0


def test_grafo_3_regular_tem_grau_3() -> None:
    p = grafo_3_regular(8)
    grau = dict.fromkeys(range(8), 0)
    for i, j, _ in p.edges:
        grau[i] += 1
        grau[j] += 1
    assert set(grau.values()) == {3}
    assert len(p.edges) == 8 * 3 // 2  # 3-regular: N·3/2 arestas


@pytest.mark.parametrize("n", [3, 5, 7])
def test_grafo_3_regular_recusa_n_impar_ou_pequeno(n: int) -> None:
    with pytest.raises(MaxCutError):
        grafo_3_regular(n)


def test_aresta_invalida_levanta() -> None:
    with pytest.raises(MaxCutError):
        MaxCutProblem(name="x", n_nodes=3, edges=((0, 0, 1.0),), seed=1)  # laço


# --------------------------------------------------------------- QAOA


def test_qaoa_aproxima_o_otimo_do_quadrado() -> None:
    """No quadrado (bipartido), o QAOA deve chegar perto do ótimo (4)."""
    r = qaoa_maxcut(QUADRADO, p=2)
    assert 0.0 < r["expected_cut"] <= 4.0
    assert r["most_probable_cut"] == 4.0  # o bitstring mais provável é o corte ótimo


def test_qar_em_0_1_e_ressalva_presente() -> None:
    rel = benchmark_maxcut(QUADRADO, ps=(1, 2))
    assert rel["otimo_classico_exato"] == 4.0
    for ponto in rel["curva_qar_por_p"]:
        assert 0.0 < ponto["qar"] <= 1.0  # QAR ≤ 1 por construção
    assert "não vantagem quântica" in rel["ressalva"]


def test_curva_tende_a_melhorar_com_p() -> None:
    """Mais camadas não pioram a aproximação (tendência não-decrescente)."""
    rel = benchmark_maxcut(QUADRADO, ps=(1, 2, 3))
    qars = [ponto["qar"] for ponto in rel["curva_qar_por_p"]]
    assert qars[-1] >= qars[0] - 1e-6


def test_reprodutivel_por_construcao() -> None:
    """Determinístico: mesma instância → mesma curva (sem RNG)."""
    a = benchmark_maxcut(QUADRADO, ps=(1,))
    b = benchmark_maxcut(QUADRADO, ps=(1,))
    assert a == b


def test_qaoa_parametros_invalidos_levantam() -> None:
    with pytest.raises(MaxCutError):
        qaoa_maxcut(QUADRADO, p=0)
    with pytest.raises(MaxCutError):
        qaoa_maxcut(QUADRADO, p=1, grid=1)
