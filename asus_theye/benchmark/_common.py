"""Internal helpers shared by benchmark adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from asus_theye.problem import BenchmarkProblem


def normalize_problem(problem: BenchmarkProblem | Mapping[str, Any]) -> BenchmarkProblem:
    if isinstance(problem, BenchmarkProblem):
        return problem
    try:
        return BenchmarkProblem(
            name=str(problem.get("name", "custom_problem")),
            values=tuple(float(value) for value in problem["values"]),
            weights=tuple(float(weight) for weight in problem["weights"]),
            capacity=float(problem["capacity"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("problem must define numeric values, weights and capacity") from exc


def best_feasible(problem: BenchmarkProblem) -> tuple[tuple[int, ...], float, int]:
    best_bits = (0,) * problem.variable_count
    best_score = problem.score(best_bits)
    evaluated = 0
    for bits in problem.candidates():
        evaluated += 1
        score = problem.score(bits)
        if problem.is_feasible(bits) and (
            score > best_score or (score == best_score and bits < best_bits)
        ):
            best_bits, best_score = bits, score
    return best_bits, best_score, evaluated
