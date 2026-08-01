"""QUBO construction and deterministic local solving measurements."""

from __future__ import annotations

import time
from typing import Any

from asus_theye.audit import AuditLedger
from asus_theye.problem import BenchmarkProblem

from ._common import best_feasible, normalize_problem


def _build_qubo(problem: BenchmarkProblem) -> dict[tuple[int, int], float]:
    """Build a binary objective with a squared capacity penalty.

    The matrix is retained as benchmark evidence; the exact local resolver enforces
    feasibility directly so that discretizing slack cannot distort the baseline.
    """

    penalty = max(sum(abs(value) for value in problem.values), 1.0)
    terms: dict[tuple[int, int], float] = {}
    for index, (value, weight) in enumerate(zip(problem.values, problem.weights, strict=True)):
        terms[(index, index)] = -value + penalty * (weight * weight - 2 * problem.capacity * weight)
    for left in range(problem.variable_count):
        for right in range(left + 1, problem.variable_count):
            coefficient = 2 * penalty * problem.weights[left] * problem.weights[right]
            if coefficient:
                terms[(left, right)] = coefficient
    return terms


def run_qubo_benchmark(
    problem: BenchmarkProblem | dict[str, Any], *, ledger: AuditLedger | None = None
) -> dict[str, Any]:
    normalized = normalize_problem(problem)
    build_started = time.perf_counter()
    qubo = _build_qubo(normalized)
    build_time_ms = (time.perf_counter() - build_started) * 1000

    solve_started = time.perf_counter()
    solution, score, _ = best_feasible(normalized)
    solve_time_ms = (time.perf_counter() - solve_started) * 1000

    n = normalized.variable_count
    quadratic_terms = sum(1 for left, right in qubo if left != right)
    possible_quadratic_terms = n * (n - 1) / 2
    result = {
        "solver": "qubo",
        "variables": n,
        "quadratic_terms": quadratic_terms,
        "density": quadratic_terms / possible_quadratic_terms if possible_quadratic_terms else 0.0,
        "build_time_ms": build_time_ms,
        "solve_time_ms": solve_time_ms,
        "execution_time_ms": build_time_ms + solve_time_ms,
        "score": score,
        "solution": list(solution),
    }
    if ledger:
        ledger.append("benchmark.qubo", result)
    return result
