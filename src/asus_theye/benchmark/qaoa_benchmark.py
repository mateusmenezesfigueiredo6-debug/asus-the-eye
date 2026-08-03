"""Controlled dependency-free state-vector QAOA simulator.

This module intentionally contains no IBM Runtime client and therefore cannot
submit a real QPU job. An authorized hardware adapter can be added separately.
"""

from __future__ import annotations

import cmath
import math
import random
import time
from typing import Any

from asus_theye.audit import AuditLedger
from asus_theye.problem import BenchmarkProblem

from ._common import best_feasible, normalize_problem

LOCAL_BACKENDS = frozenset({"local_simulator", "fake_backend"})


def run_qaoa_benchmark(
    problem: BenchmarkProblem | dict[str, Any],
    *,
    layers: int = 2,
    shots: int = 1_024,
    seed: int = 42,
    backend: str = "local_simulator",
    ledger: AuditLedger | None = None,
) -> dict[str, Any]:
    """Optimize a small QAOA circuit locally and sample its state vector."""

    if backend not in LOCAL_BACKENDS:
        raise PermissionError("benchmark QAOA accepts only controlled local or fake backends")
    if layers < 1 or shots < 1:
        raise ValueError("layers and shots must be positive")

    normalized = normalize_problem(problem)
    started = time.perf_counter()
    state_count = 1 << normalized.variable_count
    states = [tuple((state >> qubit) & 1 for qubit in range(normalized.variable_count)) for state in range(state_count)]
    optimum_bits, optimum_score, _ = best_feasible(normalized)
    penalty = max(sum(abs(value) for value in normalized.values), 1.0) + 1.0
    objectives = []
    for bits in states:
        weight = sum(item_weight * bit for item_weight, bit in zip(normalized.weights, bits, strict=True))
        overload = max(0.0, weight - normalized.capacity)
        objectives.append(normalized.score(bits) - penalty * overload * overload)
    objective_scale = max(max(abs(value) for value in objectives), 1.0)
    normalized_objectives = [value / objective_scale for value in objectives]

    def circuit(gamma: float, beta: float) -> list[complex]:
        amplitude = 1 / math.sqrt(state_count)
        statevector = [complex(amplitude)] * state_count
        for _ in range(layers):
            statevector = [
                value * cmath.exp(1j * gamma * objective)
                for value, objective in zip(statevector, normalized_objectives, strict=True)
            ]
            cosine, sine = math.cos(beta), math.sin(beta)
            for qubit in range(normalized.variable_count):
                mask = 1 << qubit
                for state in range(state_count):
                    if state & mask:
                        continue
                    paired = state | mask
                    left, right = statevector[state], statevector[paired]
                    statevector[state] = cosine * left - 1j * sine * right
                    statevector[paired] = cosine * right - 1j * sine * left
        return statevector

    angle_grid = (math.pi / 12, math.pi / 6, math.pi / 4, math.pi / 3, 5 * math.pi / 12)
    best_expected = -math.inf
    best_angles = (angle_grid[0], angle_grid[0])
    best_statevector: list[complex] = []
    for gamma in angle_grid:
        for beta in angle_grid:
            candidate = circuit(gamma, beta)
            expected = sum(
                abs(amplitude) ** 2 * objective for amplitude, objective in zip(candidate, objectives, strict=True)
            )
            if expected > best_expected:
                best_expected = expected
                best_angles = (gamma, beta)
                best_statevector = candidate

    probabilities = [abs(amplitude) ** 2 for amplitude in best_statevector]
    rng = random.Random(seed)
    sampled_states = rng.choices(range(state_count), weights=probabilities, k=shots)
    feasible_samples = [states[state] for state in sampled_states if normalized.is_feasible(states[state])]
    solution = max(
        feasible_samples or [(0,) * normalized.variable_count],
        key=lambda bits: (normalized.score(bits), tuple(-bit for bit in bits)),
    )
    score = normalized.score(solution)
    elapsed_ms = (time.perf_counter() - started) * 1000
    optimal_states = {
        index
        for index, bits in enumerate(states)
        if normalized.is_feasible(bits) and normalized.score(bits) == optimum_score
    }
    fidelity = sum(probabilities[index] for index in optimal_states)
    result = {
        "solver": "qaoa",
        "backend": backend,
        "shots": shots,
        "layers": layers,
        "depth": normalized.variable_count * (2 * layers + 1),
        "execution_time_ms": elapsed_ms,
        "score": score,
        "solution": list(solution),
        "fidelity": fidelity,
        "expected_objective": best_expected,
        "optimized_angles": {"gamma": best_angles[0], "beta": best_angles[1]},
        "seed": seed,
        "hardware_execution": False,
        "reference_solution": list(optimum_bits),
    }
    if ledger:
        ledger.append("benchmark.qaoa_local", result)
    return result
