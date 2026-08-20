# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Instrumentation for the exhaustive deterministic baseline solver."""

from __future__ import annotations

import resource
import time
from datetime import datetime, timezone
from typing import Any

from asus_theye import __version__
from asus_theye.audit import AuditLedger
from asus_theye.problem import BenchmarkProblem

from ._common import best_feasible, normalize_problem


def _rss_mb() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return float(usage) / 1024


def run_classical_benchmark(
    problem: BenchmarkProblem | dict[str, Any], *, ledger: AuditLedger | None = None
) -> dict[str, Any]:
    """Run and measure the exact local baseline; no network resources are used."""

    normalized = normalize_problem(problem)
    memory_before = _rss_mb()
    started = time.perf_counter()
    solution, score, combinations = best_feasible(normalized)
    elapsed_ms = (time.perf_counter() - started) * 1000
    memory_after = _rss_mb()
    result = {
        "solver": "classical",
        "execution_time_ms": elapsed_ms,
        "memory_mb": max(memory_before, memory_after),
        "combinations_evaluated": combinations,
        "score": score,
        "solution": list(solution),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "solver_version": __version__,
    }
    if ledger:
        ledger.append("benchmark.classical", result)
    return result
