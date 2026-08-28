# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seleção quântica de carteira de previsões — "a metade que faltava".

Recuperado do pipeline ASUS de 2026-07-30 (acervo da conta antiga, validado à
época em QPU real ibm_marrakesh) e portado para o estilo desta casa: Python
puro, sem numpy/qiskit, statevector local controlado e selagem no ledger.

O problema: dado um conjunto de previsões calibradas (cada uma com um `edge` —
vantagem esperada — e um `risco`), escolher EXATAMENTE K para publicar/operar,
evitando concentrar posições correlacionadas. Vira um QUBO:

    minimizar  -Σ edge_i·x_i
               + λ·Σ corr_ij·(risco_i+risco_j)/2 · x_i·x_j
               + ρ·(Σ x_i − K)²

A decodificação usa REPARO CLÁSSICO: entre os estados amostrados pelo QAOA,
vale o melhor que respeita "exatamente K". O resultado sempre carrega o ótimo
exato ao lado (`bate_otimo`) — benchmark honesto, nunca alegação cega.
"""

from __future__ import annotations

import cmath
import math
import random
import time
from dataclasses import dataclass
from typing import Any

from asus_theye.audit import AuditLedger

MAX_QUBITS = 12
_GRADE_ANGULOS = (math.pi / 12, math.pi / 6, math.pi / 4, math.pi / 3, 5 * math.pi / 12)


@dataclass(frozen=True)
class Candidato:
    """Uma previsão candidata à carteira."""

    codigo: str
    edge: float
    risco: float
    descricao: str = ""

    def __post_init__(self) -> None:
        if not self.codigo:
            raise ValueError("candidato exige codigo")
        for campo, valor in (("edge", self.edge), ("risco", self.risco)):
            if not math.isfinite(valor):
                raise ValueError(f"{campo} de {self.codigo} deve ser finito")
        if not 0.0 <= self.risco <= 1.0:
            raise ValueError(f"risco de {self.codigo} deve estar em [0, 1]")


def _validar_correlacao(correlacao: dict[tuple[int, int], float], n: int) -> dict[tuple[int, int], float]:
    """Normaliza pares (i, j) com i < j; recusa índices fora do domínio."""

    normalizada: dict[tuple[int, int], float] = {}
    for (i, j), valor in correlacao.items():
        if i == j or not (0 <= i < n and 0 <= j < n):
            raise ValueError(f"par de correlação inválido: ({i}, {j})")
        if not math.isfinite(valor) or not -1.0 <= valor <= 1.0:
            raise ValueError(f"correlação ({i}, {j}) deve estar em [-1, 1]")
        chave = (i, j) if i < j else (j, i)
        anterior = normalizada.get(chave)
        if anterior is not None and anterior != valor:
            raise ValueError(f"correlação ({i}, {j}) declarada duas vezes com valores diferentes")
        normalizada[chave] = valor
    return normalizada


def construir_qubo(
    candidatos: list[Candidato],
    correlacao: dict[tuple[int, int], float],
    k: int,
    lam: float,
    pen: float,
) -> dict[tuple[int, int], float]:
    """Monta o QUBO esparso da seleção (formato (i, j) -> coeficiente, i <= j)."""

    n = len(candidatos)
    termos: dict[tuple[int, int], float] = {}
    for i, cand in enumerate(candidatos):
        termos[(i, i)] = -cand.edge + pen * (1 - 2 * k)
    for i in range(n):
        for j in range(i + 1, n):
            coeficiente = 2.0 * pen
            corr = correlacao.get((i, j), 0.0)
            if corr:
                coeficiente += lam * corr * (candidatos[i].risco + candidatos[j].risco) / 2.0
            termos[(i, j)] = coeficiente
    return termos


def _objetivo(qubo: dict[tuple[int, int], float], bits: tuple[int, ...]) -> float:
    total = 0.0
    for (i, j), coeficiente in qubo.items():
        if bits[i] and bits[j]:
            total += coeficiente
    return total


def _otimo_exato(
    qubo: dict[tuple[int, int], float], n: int, k: int
) -> tuple[tuple[int, ...], float]:
    """Varre todos os estados com exatamente K escolhas — a referência honesta."""

    melhor_bits: tuple[int, ...] | None = None
    melhor_valor = math.inf
    for estado in range(1 << n):
        bits = tuple((estado >> q) & 1 for q in range(n))
        if sum(bits) != k:
            continue
        valor = _objetivo(qubo, bits)
        if valor < melhor_valor or (valor == melhor_valor and (melhor_bits is None or bits < melhor_bits)):
            melhor_bits, melhor_valor = bits, valor
    if melhor_bits is None:  # pragma: no cover - guardado por validação de k
        raise ValueError("nenhum estado com exatamente K escolhas")
    return melhor_bits, melhor_valor


def _amostrar_qaoa(
    qubo: dict[tuple[int, int], float],
    n: int,
    *,
    layers: int,
    shots: int,
    seed: int,
) -> list[tuple[int, ...]]:
    """Statevector QAOA local (mesma mecânica controlada do qaoa_benchmark)."""

    state_count = 1 << n
    estados = [tuple((estado >> q) & 1 for q in range(n)) for estado in range(state_count)]
    objetivos = [_objetivo(qubo, bits) for bits in estados]
    escala = max(max(abs(v) for v in objetivos), 1.0)
    # QAOA maximiza a fase esperada; nosso QUBO minimiza — inverte o sinal.
    normalizados = [-v / escala for v in objetivos]

    def circuito(gamma: float, beta: float) -> list[complex]:
        amplitude = 1 / math.sqrt(state_count)
        statevector = [complex(amplitude)] * state_count
        for _ in range(layers):
            statevector = [
                valor * cmath.exp(1j * gamma * objetivo)
                for valor, objetivo in zip(statevector, normalizados, strict=True)
            ]
            cosseno, seno = math.cos(beta), math.sin(beta)
            for qubit in range(n):
                mascara = 1 << qubit
                for estado in range(state_count):
                    if estado & mascara:
                        continue
                    par = estado | mascara
                    esquerda, direita = statevector[estado], statevector[par]
                    statevector[estado] = cosseno * esquerda - 1j * seno * direita
                    statevector[par] = cosseno * direita - 1j * seno * esquerda
        return statevector

    melhor_esperado = -math.inf
    melhor_statevector: list[complex] = []
    for gamma in _GRADE_ANGULOS:
        for beta in _GRADE_ANGULOS:
            candidato = circuito(gamma, beta)
            esperado = sum(
                abs(amplitude) ** 2 * objetivo
                for amplitude, objetivo in zip(candidato, normalizados, strict=True)
            )
            if esperado > melhor_esperado:
                melhor_esperado = esperado
                melhor_statevector = candidato

    probabilidades = [abs(amplitude) ** 2 for amplitude in melhor_statevector]
    rng = random.Random(seed)
    amostras = rng.choices(range(state_count), weights=probabilidades, k=shots)
    return [estados[a] for a in amostras]


def _reparo_classico(
    amostras: list[tuple[int, ...]],
    qubo: dict[tuple[int, int], float],
    k: int,
) -> tuple[tuple[int, ...], float]:
    """Entre os estados amostrados, o melhor com exatamente K (fallback: melhor geral)."""

    avaliadas = sorted(
        {bits: _objetivo(qubo, bits) for bits in amostras}.items(), key=lambda item: (item[1], item[0])
    )
    com_k = [(bits, valor) for bits, valor in avaliadas if sum(bits) == k]
    escolhida = com_k[0] if com_k else avaliadas[0]
    return escolhida


def selecionar_carteira(
    candidatos: list[Candidato],
    *,
    correlacao: dict[tuple[int, int], float] | None = None,
    k: int = 3,
    lam: float = 1.2,
    pen: float = 3.0,
    layers: int = 2,
    shots: int = 2_048,
    seed: int = 7,
    ledger: AuditLedger | None = None,
) -> dict[str, Any]:
    """Escolhe K previsões via QAOA local, sempre comparando com o ótimo exato."""

    n = len(candidatos)
    if n < 2:
        raise ValueError("seleção exige pelo menos 2 candidatos")
    if n > MAX_QUBITS:
        raise ValueError(f"seleção local aceita no máximo {MAX_QUBITS} candidatos (recebeu {n})")
    if not 1 <= k <= n:
        raise ValueError("k deve estar entre 1 e o número de candidatos")
    if layers < 1 or shots < 1:
        raise ValueError("layers e shots devem ser positivos")
    codigos = [c.codigo for c in candidatos]
    if len(set(codigos)) != n:
        raise ValueError("códigos de candidatos devem ser únicos")

    corr = _validar_correlacao(correlacao or {}, n)
    iniciado = time.perf_counter()
    qubo = construir_qubo(candidatos, corr, k, lam, pen)

    otimo_bits, otimo_valor = _otimo_exato(qubo, n, k)
    amostras = _amostrar_qaoa(qubo, n, layers=layers, shots=shots, seed=seed)
    bits, valor = _reparo_classico(amostras, qubo, k)

    escolhidos = [codigos[i] for i in range(n) if bits[i]]
    edge_total = sum(candidatos[i].edge for i in range(n) if bits[i])
    decorrido_ms = (time.perf_counter() - iniciado) * 1000

    resultado = {
        "solver": "selecao_carteira_qaoa",
        "backend": "local_simulator",
        "hardware_execution": False,
        "k": k,
        "lam": lam,
        "pen": pen,
        "layers": layers,
        "shots": shots,
        "seed": seed,
        "candidatos": codigos,
        "selecao": escolhidos,
        "edge_total": round(edge_total, 6),
        "objetivo": round(valor, 6),
        "selecao_otima": [codigos[i] for i in range(n) if otimo_bits[i]],
        "objetivo_otimo": round(otimo_valor, 6),
        "bate_otimo": bits == otimo_bits,
        "execution_time_ms": decorrido_ms,
        "origem": "portado do pipeline ASUS 2026-07-30 (validado em ibm_marrakesh)",
    }
    if ledger:
        ledger.append("benchmark.selecao_carteira", resultado)
    return resultado


def candidatos_demo() -> tuple[list[Candidato], dict[tuple[int, int], float]]:
    """A amostra de 8 candidatos do pipeline recuperado, preservada como fixture."""

    candidatos = [
        Candidato("KEV-01", 0.16, 0.30, "Falha crítica explorada em 30d"),
        Candidato("KEV-02", 0.04, 0.25, "Patch atrasa além do prazo"),
        Candidato("MKT-11", 0.08, 0.55, "Evento macro sobe até sexta"),
        Candidato("MKT-12", 0.18, 0.45, "Índice fecha acima do strike"),
        Candidato("KEV-03", 0.20, 0.35, "CVE vira KEV oficial em 14d"),
        Candidato("MKT-13", 0.03, 0.60, "Volatilidade acima da média"),
        Candidato("KEV-04", 0.06, 0.20, "Fornecedor confirma correção"),
        Candidato("MKT-14", 0.17, 0.40, "Faixa de preço se mantém"),
    ]
    correlacao = {(0, 4): 0.7, (4, 6): 0.5, (0, 6): 0.4, (3, 7): 0.6, (2, 5): 0.5, (1, 4): 0.3}
    return candidatos, correlacao
