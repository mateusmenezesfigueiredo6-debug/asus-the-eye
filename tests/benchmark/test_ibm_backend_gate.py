# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gate tests for the IBM hardware adapter — must pass with or without qiskit."""

from __future__ import annotations

import pytest

from asus_theye.benchmark.ibm_backend import (
    EXECUTE_ENV_FLAG,
    HardwareGateClosed,
    execution_gate_open,
    run_on_hardware,
)
from asus_theye.problem import load_demo_problem


def test_gate_closed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(EXECUTE_ENV_FLAG, raising=False)
    assert execution_gate_open() is False


def test_gate_requires_exact_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(EXECUTE_ENV_FLAG, "true")
    assert execution_gate_open() is False
    monkeypatch.setenv(EXECUTE_ENV_FLAG, "1")
    assert execution_gate_open() is True


def test_hardware_submission_blocked_without_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(EXECUTE_ENV_FLAG, raising=False)
    with pytest.raises(HardwareGateClosed, match="explicit human approval"):
        run_on_hardware(load_demo_problem())


def test_circuit_builder_matches_problem_size() -> None:
    pytest.importorskip("qiskit")
    from asus_theye.benchmark.ibm_backend import build_qaoa_circuit

    problem = load_demo_problem()
    circuit = build_qaoa_circuit(problem, layers=2)
    assert circuit.num_qubits == problem.variable_count
    assert circuit.depth() > 0
    # measure_all adds classical bits for every qubit.
    assert circuit.num_clbits == problem.variable_count
