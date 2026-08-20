from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from asus_theye.audit import verify_ledger
from asus_theye.benchmark.classical_benchmark import run_classical_benchmark
from asus_theye.benchmark.metrics import quantum_advantage_ratio
from asus_theye.benchmark.qaoa_benchmark import run_qaoa_benchmark
from asus_theye.benchmark.qubo_benchmark import run_qubo_benchmark
from asus_theye.benchmark.runner import run_benchmark_suite
from asus_theye.dashboard import benchmark_page
from asus_theye.dashboard.benchmark import _svg_bar_chart
from asus_theye.problem import load_demo_problem


@pytest.fixture
def problem():
    return load_demo_problem()


def test_classical_benchmark_executes(problem):
    result = run_classical_benchmark(problem)
    assert result["solver"] == "classical"
    assert result["score"] == 28.0
    assert result["combinations_evaluated"] == 64
    assert result["execution_time_ms"] >= 0
    assert result["solver_version"] == "0.2.0"


def test_qubo_generates_metrics(problem):
    result = run_qubo_benchmark(problem)
    assert result["solver"] == "qubo"
    assert result["variables"] == 6
    assert result["quadratic_terms"] == 15
    assert result["density"] == 1.0
    assert result["score"] == 28.0


def test_qaoa_local_is_reproducible(problem):
    first = run_qaoa_benchmark(problem, shots=128, seed=7)
    second = run_qaoa_benchmark(problem, shots=128, seed=7)
    assert first["backend"] == "local_simulator"
    assert first["hardware_execution"] is False
    assert first["solution"] == second["solution"]
    assert first["score"] == second["score"]
    assert 0 <= first["fidelity"] <= 1


@pytest.mark.parametrize(
    ("qaoa", "classical", "expected", "phrase"),
    [
        (11, 10, 1.1, "não constitui prova científica"),
        (10, 10, 1.0, "empate"),
        (9, 10, 0.9, "clássico superior"),
    ],
)
def test_qar_calculates_and_is_conservative(qaoa, classical, expected, phrase):
    metric = quantum_advantage_ratio(qaoa, classical)
    assert metric["qar"] == pytest.approx(expected)
    assert phrase in metric["interpretation"]


def test_report_and_audit_ledger_are_created(tmp_path: Path, problem):
    report, path = run_benchmark_suite(problem=problem, output_dir=tmp_path, shots=64)
    assert path == tmp_path / "latest.json"
    assert json.loads(path.read_text())["project"] == "ASUS THE EYE"
    assert report["metrics"]["stability"]["runs"] == 10
    assert (tmp_path / "history.jsonl").exists()
    assert verify_ledger(tmp_path / "ledger.jsonl")
    events = [json.loads(line)["event"] for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert {
        "benchmark.classical",
        "benchmark.qubo",
        "benchmark.qaoa_local",
        "benchmark.metrics",
    } <= set(events)
    assert {"telemetry.performance", "telemetry.cost"} <= set(events)


def test_no_real_qpu_or_network_call_happens(monkeypatch, tmp_path: Path, problem):
    def blocked(*args, **kwargs):
        raise AssertionError("network access is forbidden in local benchmarks")

    monkeypatch.setattr(socket, "create_connection", blocked)
    report, _ = run_benchmark_suite(problem=problem, output_dir=tmp_path, shots=32)
    assert report["results"]["qaoa"]["hardware_execution"] is False
    assert report["telemetry"]["cost"]["qpu_time_ms"] == 0
    with pytest.raises(PermissionError):
        run_qaoa_benchmark(problem, backend="ibm_quantum")


def test_dashboard_contains_required_cards_and_charts(tmp_path: Path, problem):
    _, report_path = run_benchmark_suite(problem=problem, output_dir=tmp_path, shots=32)
    page = benchmark_page(report_path)
    for label in (
        "Best score",
        "Best time",
        "QAR",
        "Stability",
        "Score comparison",
        "Execution time",
        "History",
    ):
        assert label in page
    assert page.count("<svg") == 3
    assert 'aria-label="Score comparison"' in page
    assert 'aria-label="Execution time"' in page
    assert 'aria-label="History"' in page
    assert "<script>" not in page


def test_svg_chart_falls_back_to_text_when_all_values_are_non_positive():
    chart = _svg_bar_chart(
        [("alpha", -1.0), ("beta", 0.0)],
        aria_label="negative chart",
        formatter="{value:.1f}",
    )
    assert "<svg" in chart
    assert "alpha" in chart and "-1.0" in chart
    assert "beta" in chart and "0.0" in chart
