"""Max-Cut 12–16 qubits — benchmark técnico honesto (QAOA vs ótimo exato).

Implementa docs/architecture/QUANTUM_12_16_QUBITS.md. Auto-contido: não toca o
caminho do knapsack. Simulação LOCAL por statevector (numpy); QPU real fica
atrás do gate fechado — este módulo nunca a chama.

Honestidade embutida: o clássico aqui é o ótimo EXATO (força bruta em 2^N),
viável até ~20 qubits. Logo o QAR = aproximação_QAOA / ótimo ∈ (0, 1], por
construção — mede a QUALIDADE DA APROXIMAÇÃO, **não** vantagem quântica (que
exigiria um regime onde o clássico não alcança o ótimo). O relatório diz isso.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

Aresta = tuple[int, int, float]


class MaxCutError(RuntimeError):
    """Problema ou parâmetro inválido. Sempre levanta."""


@dataclass(frozen=True)
class MaxCutProblem:
    """Instância de Max-Cut determinística e serializável (N nós → N qubits)."""

    name: str
    n_nodes: int
    edges: tuple[Aresta, ...]
    seed: int

    def __post_init__(self) -> None:
        if not 2 <= self.n_nodes <= 20:
            raise MaxCutError(f"n_nodes deve estar em [2, 20], veio {self.n_nodes}")
        for i, j, w in self.edges:
            if not (0 <= i < self.n_nodes and 0 <= j < self.n_nodes) or i == j:
                raise MaxCutError(f"aresta inválida ({i},{j}) para {self.n_nodes} nós")
            if w <= 0:
                raise MaxCutError(f"peso deve ser > 0, veio {w}")

    @property
    def variable_count(self) -> int:
        return self.n_nodes

    def cut(self, bits: tuple[int, ...]) -> float:
        """Valor do corte: soma dos pesos das arestas cujos extremos diferem."""
        if len(bits) != self.n_nodes:
            raise MaxCutError(f"esperado {self.n_nodes} bits, veio {len(bits)}")
        return float(sum(w for i, j, w in self.edges if bits[i] != bits[j]))

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "n_nodes": self.n_nodes,
            "edges": [list(e) for e in self.edges],
            "seed": self.seed,
        }


def grafo_3_regular(n_nodes: int, *, seed: int = 42) -> MaxCutProblem:
    """Grafo 3-regular determinístico (anel + corda diametral). N par, ≥ 4.

    Cada nó liga a i±1 (anel, grau 2) e a i+N/2 (corda, grau 1) → grau 3. Nada de
    aleatório em runtime: a construção é fixa; ``seed`` viaja como metadado para
    variantes futuras.
    """
    if n_nodes < 4 or n_nodes % 2 != 0:
        raise MaxCutError(f"grafo 3-regular exige N par ≥ 4, veio {n_nodes}")
    arestas: set[tuple[int, int]] = set()
    metade = n_nodes // 2

    def par(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)

    for i in range(n_nodes):
        arestas.add(par(i, (i + 1) % n_nodes))  # anel
    for i in range(metade):
        arestas.add(par(i, i + metade))  # corda diametral
    edges = tuple((i, j, 1.0) for i, j in sorted(arestas))
    return MaxCutProblem(name=f"maxcut_3reg_n{n_nodes}", n_nodes=n_nodes, edges=edges, seed=seed)


def otimo_forca_bruta(problem: MaxCutProblem) -> tuple[tuple[int, ...], float]:
    """Ótimo EXATO por varredura de 2^N. O teto real contra o qual o QAOA mede."""
    n = problem.n_nodes
    cuts = _valores_de_corte(problem)
    melhor = int(np.argmax(cuts))
    bits = tuple((melhor >> q) & 1 for q in range(n))
    return bits, float(cuts[melhor])


def _valores_de_corte(problem: MaxCutProblem) -> np.ndarray:
    """Vetor de comprimento 2^N com o valor do corte de cada bitstring."""
    n = problem.n_nodes
    estados = np.arange(1 << n)
    cuts = np.zeros(1 << n)
    for i, j, w in problem.edges:
        bi = (estados >> i) & 1
        bj = (estados >> j) & 1
        cuts += w * (bi ^ bj)
    return cuts


def _aplicar_mixer(estado: np.ndarray, beta: float, n: int) -> np.ndarray:
    """exp(-i·beta·ΣX) = produto de exp(-i·beta·X) por qubit."""
    c, s = np.cos(beta), -1j * np.sin(beta)
    m = np.array([[c, s], [s, c]])
    vetor = estado.reshape([2] * n)
    for q in range(n):
        vetor = np.moveaxis(vetor, q, 0)
        forma = vetor.shape
        vetor = (m @ vetor.reshape(2, -1)).reshape(forma)
        vetor = np.moveaxis(vetor, 0, q)
    return vetor.reshape(-1)


def qaoa_maxcut(problem: MaxCutProblem, *, p: int, grid: int = 12) -> dict[str, Any]:
    """QAOA de p camadas (mesmos γ,β em todas), otimizado por grid determinístico.

    Devolve ``expected_cut`` (corte médio ⟨C⟩ — a aproximação honesta),
    ``most_probable_cut`` (corte do bitstring mais provável) e os ângulos ótimos.
    """
    if p < 1 or grid < 2:
        raise MaxCutError("p ≥ 1 e grid ≥ 2")
    n = problem.n_nodes
    cuts = _valores_de_corte(problem)
    dim = 1 << n
    uniforme = np.full(dim, 1.0 / np.sqrt(dim), dtype=complex)

    melhor_esperado = -1.0
    melhor_gamma = 0.0
    melhor_beta = 0.0
    melhor_probs: np.ndarray = np.abs(uniforme) ** 2
    for gamma in np.linspace(0.0, np.pi, grid):
        fase_cost = np.exp(-1j * gamma * cuts)
        for beta in np.linspace(0.0, np.pi / 2, grid):
            estado = uniforme.copy()
            for _ in range(p):
                estado = estado * fase_cost  # camada de custo (diagonal)
                estado = _aplicar_mixer(estado, float(beta), n)  # camada de mixer
            probs = np.abs(estado) ** 2
            esperado = float(np.dot(probs, cuts))
            if esperado > melhor_esperado:
                melhor_esperado, melhor_gamma, melhor_beta, melhor_probs = esperado, float(gamma), float(beta), probs

    return {
        "p": p,
        "expected_cut": round(melhor_esperado, 6),
        "most_probable_cut": float(cuts[int(np.argmax(melhor_probs))]),
        "gamma": round(melhor_gamma, 6),
        "beta": round(melhor_beta, 6),
    }


def benchmark_maxcut(problem: MaxCutProblem, *, ps: tuple[int, ...] = (1, 2, 3), grid: int = 12) -> dict[str, Any]:
    """Curva QAR × p contra o ótimo exato, com a ressalva honesta obrigatória."""
    _bits, otimo = otimo_forca_bruta(problem)
    curva = []
    for p in ps:
        r = qaoa_maxcut(problem, p=p, grid=grid)
        qar = r["expected_cut"] / otimo if otimo > 0 else 1.0
        curva.append({**r, "qar": round(qar, 6)})
    return {
        "problem": problem.as_dict(),
        "n_qubits": problem.n_nodes,
        "otimo_classico_exato": otimo,
        "curva_qar_por_p": curva,
        "ressalva": (
            "QAR ≤ 1,0 por construção: o clássico aqui é o ótimo EXATO (força bruta em 2^N), "
            "viável até ~20 qubits. Este benchmark mede a QUALIDADE DA APROXIMAÇÃO do QAOA "
            "contra o ótimo, não vantagem quântica — que exigiria um regime onde o clássico não "
            "alcança o ótimo. A curva QAR × p é publicada inteira; o tempo do QAOA (simulado) "
            "não é comparável a tempo de QPU real."
        ),
    }
