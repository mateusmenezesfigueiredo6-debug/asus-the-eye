"""Comparison metrics with deliberately conservative interpretations."""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable
from typing import Any


def quantum_advantage_ratio(score_qaoa: float, score_classical: float) -> dict[str, Any]:
    """Compare quality scores without claiming scientific quantum advantage."""

    if score_classical == 0:
        qar = math.inf if score_qaoa > 0 else 1.0
    else:
        qar = score_qaoa / score_classical
    tolerance = 1e-12
    if qar > 1.0 + tolerance:
        interpretation = "possível vantagem; sinal preliminar, não constitui prova científica"
    elif math.isclose(qar, 1.0, rel_tol=tolerance, abs_tol=tolerance):
        interpretation = "empate nas condições atuais; não constitui prova científica"
    else:
        interpretation = "clássico superior nas condições atuais"
    return {"qar": qar, "interpretation": interpretation}


def speed_ratio(classical_time_ms: float, quantum_time_ms: float) -> float:
    if quantum_time_ms < 0 or classical_time_ms < 0:
        raise ValueError("execution times cannot be negative")
    if quantum_time_ms == 0:
        return math.inf if classical_time_ms > 0 else 1.0
    return classical_time_ms / quantum_time_ms


def quality_gap(score_classical: float, score_quantum: float) -> float:
    return score_classical - score_quantum


def stability_score(
    execute: Callable[[int], float | dict[str, Any]], *, n: int = 10, seed: int = 42
) -> dict[str, Any]:
    """Execute a solver repeatedly and summarize score dispersion."""

    if n < 2:
        raise ValueError("stability requires at least two executions")
    scores: list[float] = []
    for offset in range(n):
        result = execute(seed + offset)
        score = result["score"] if isinstance(result, dict) else result
        scores.append(float(score))
    return {
        "runs": n,
        "mean": statistics.fmean(scores),
        "standard_deviation": statistics.pstdev(scores),
        "variance": statistics.pvariance(scores),
        "scores": scores,
    }


# Explicit calculation names preserve a discoverable API for integrations.
calculate_qar = quantum_advantage_ratio
calculate_speed_ratio = speed_ratio
calculate_quality_gap = quality_gap
calculate_stability = stability_score
