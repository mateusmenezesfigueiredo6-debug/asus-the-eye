"""Orchestration for a complete, reproducible benchmark suite."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from asus_theye.audit import AuditLedger
from asus_theye.problem import BenchmarkProblem, load_demo_problem
from asus_theye.telemetry import collect_cost_telemetry, collect_performance_telemetry

from .classical_benchmark import run_classical_benchmark
from .metrics import quality_gap, quantum_advantage_ratio, speed_ratio, stability_score
from .qaoa_benchmark import run_qaoa_benchmark
from .qubo_benchmark import run_qubo_benchmark
from .report import build_report, write_report


def _append_history(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "date": report["date"],
        "problem": report["problem"]["name"],
        "scores": {name: result["score"] for name, result in report["results"].items()},
        "times_ms": {name: result["execution_time_ms"] for name, result in report["results"].items()},
        "qar": report["metrics"]["qar"]["qar"],
        "stability": report["metrics"]["stability"]["standard_deviation"],
    }
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(summary, sort_keys=True, ensure_ascii=False) + "\n")


def run_benchmark_suite(
    *,
    problem: BenchmarkProblem | None = None,
    output_dir: str | Path = "reports/benchmark",
    shots: int = 1_024,
    layers: int = 2,
    seed: int = 42,
    stability_runs: int = 10,
) -> tuple[dict[str, Any], Path]:
    """Run all local solvers, register evidence, and persist the latest report."""

    dataset = problem or load_demo_problem()
    destination = Path(output_dir)
    ledger = AuditLedger(destination / "ledger.jsonl")
    suite_started = time.perf_counter()
    ledger.append(
        "benchmark.started",
        {
            "problem": dataset.as_dict(),
            "seed": seed,
            "shots": shots,
            "layers": layers,
            "stability_runs": stability_runs,
            "backend_policy": "local_only",
        },
    )

    classical = run_classical_benchmark(dataset, ledger=ledger)
    qubo = run_qubo_benchmark(dataset, ledger=ledger)
    qaoa = run_qaoa_benchmark(dataset, shots=shots, layers=layers, seed=seed, backend="local_simulator", ledger=ledger)
    stability = stability_score(
        lambda run_seed: run_qaoa_benchmark(
            dataset,
            shots=shots,
            layers=layers,
            seed=run_seed,
            backend="local_simulator",
        ),
        n=stability_runs,
        seed=seed,
    )
    metrics = {
        "qar": quantum_advantage_ratio(qaoa["score"], classical["score"]),
        "speed_ratio": speed_ratio(classical["execution_time_ms"], qaoa["execution_time_ms"]),
        "quality_gap": quality_gap(classical["score"], qaoa["score"]),
        "stability": stability,
    }
    ledger.append("benchmark.metrics", metrics)

    results = {"classical": classical, "qubo": qubo, "qaoa": qaoa}
    report = build_report(problem=dataset.as_dict(), results=results, metrics=metrics)
    report["telemetry"] = {
        "performance": collect_performance_telemetry(
            execution_time_ms=(time.perf_counter() - suite_started) * 1000,
            execution="benchmark_suite",
            ledger=ledger,
        ),
        "cost": collect_cost_telemetry(
            shots=shots,
            execution_time_ms=qaoa["execution_time_ms"],
            backend=qaoa["backend"],
            ledger=ledger,
        ),
    }
    report_path = write_report(report, destination / "latest.json")
    _append_history(report, destination / "history.jsonl")
    report_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
    ledger.append("benchmark.report_created", {"path": str(report_path), "sha256": report_hash})
    return report, report_path
