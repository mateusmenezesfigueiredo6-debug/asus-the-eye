# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gated IBM Quantum hardware adapter for the QAOA benchmark.

Honesty and safety gates, in order:

1. ``qiskit``/``qiskit-ibm-runtime`` are optional — importing this module
   without them raises a clear error naming the install extra.
2. Credentials are the user's own saved IBM Quantum account (or
   ``QISKIT_IBM_TOKEN``); this codebase never stores or logs tokens.
3. Without ``THE_EYE_IBM_EXECUTE=1`` only dry-run is allowed: list backends,
   queue depth and estimated usage. Submitting a real job with the gate closed
   raises :class:`HardwareGateClosed` — it never "just runs".
4. Results are labeled ``hardware_execution: True`` with the exact backend,
   and scored with the *same* objective as the local paths, so QAR comparisons
   stay honest.
"""

from __future__ import annotations

import math
import os
import time
from typing import Any

from asus_theye.problem import BenchmarkProblem

EXECUTE_ENV_FLAG = "THE_EYE_IBM_EXECUTE"


class QuantumDepsMissing(RuntimeError):
    """qiskit extras are not installed."""


class HardwareGateClosed(PermissionError):
    """A real QPU submission was attempted without the explicit gate."""


def _require_qiskit():
    try:
        from qiskit import QuantumCircuit
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    except ImportError as error:  # pragma: no cover - exercised only without extras
        raise QuantumDepsMissing("IBM Quantum support requires: pip install -e '.[quantum]'") from error
    return QuantumCircuit, generate_preset_pass_manager, QiskitRuntimeService, SamplerV2


def execution_gate_open() -> bool:
    return os.environ.get(EXECUTE_ENV_FLAG, "") == "1"


def build_qaoa_circuit(
    problem: BenchmarkProblem, layers: int = 2, gamma: float = math.pi / 6, beta: float = math.pi / 6
):
    """Build the knapsack QAOA ansatz as a Qiskit circuit.

    Mirrors the local simulator: value terms as single-qubit RZ phases, the
    capacity penalty approximated by pairwise ZZ couplings, transverse-field
    mixer. Small and shallow on purpose — this is a benchmark probe, not a
    performance claim.
    """
    QuantumCircuit, *_ = _require_qiskit()
    qubits = problem.variable_count
    circuit = QuantumCircuit(qubits)
    circuit.h(range(qubits))
    scale = max(max(abs(v) for v in problem.values), 1.0)
    for _ in range(layers):
        for index, value in enumerate(problem.values):
            circuit.rz(2 * gamma * value / scale, index)
        weight_scale = max(max(problem.weights), 1.0)
        for i in range(qubits):
            for j in range(i + 1, qubits):
                coupling = (problem.weights[i] * problem.weights[j]) / (weight_scale * weight_scale)
                if coupling:
                    circuit.rzz(2 * gamma * coupling, i, j)
        circuit.rx(2 * beta, range(qubits))
    circuit.measure_all()
    return circuit


def dry_run(problem: BenchmarkProblem, layers: int = 2, shots: int = 1_024) -> dict[str, Any]:
    """List available backends and estimate the job without submitting anything."""
    _, _, QiskitRuntimeService, _ = _require_qiskit()
    service = QiskitRuntimeService()
    backends = []
    for backend in service.backends(operational=True, simulator=False):
        status = backend.status()
        backends.append(
            {
                "name": backend.name,
                "qubits": backend.num_qubits,
                "pending_jobs": status.pending_jobs,
                "operational": status.operational,
            }
        )
    circuit = build_qaoa_circuit(problem, layers=layers)
    return {
        "mode": "dry_run",
        "hardware_execution": False,
        "gate_open": execution_gate_open(),
        "circuit_qubits": circuit.num_qubits,
        "circuit_depth": circuit.depth(),
        "shots": shots,
        "backends": sorted(backends, key=lambda item: item["pending_jobs"]),
        "note": (
            "No job was submitted. Set THE_EYE_IBM_EXECUTE=1 and pass --execute "
            "to run on hardware (uses your IBM Quantum open-plan quota)."
        ),
    }


def build_qubo_circuit(
    qubo: dict[tuple[int, int], float],
    qubits: int,
    layers: int = 2,
    gamma: float = math.pi / 6,
    beta: float = math.pi / 6,
):
    """QAOA raso para um QUBO arbitrário (diagonal → RZ, fora da diagonal → RZZ).

    Mesma filosofia do ansatz de knapsack: sonda de benchmark com ângulos
    fixos e coeficientes normalizados — não uma alegação de desempenho.
    """
    QuantumCircuit, *_ = _require_qiskit()
    circuit = QuantumCircuit(qubits)
    circuit.h(range(qubits))
    escala = max(max(abs(coef) for coef in qubo.values()), 1.0)
    for _ in range(layers):
        for (i, j), coef in qubo.items():
            if not coef:
                continue
            if i == j:
                circuit.rz(2 * gamma * coef / escala, i)
            else:
                circuit.rzz(2 * gamma * coef / escala, i, j)
        circuit.rx(2 * beta, range(qubits))
    circuit.measure_all()
    return circuit


def run_selecao_on_hardware(
    qubo: dict[tuple[int, int], float],
    qubits: int,
    k: int,
    layers: int = 2,
    shots: int = 2_048,
    backend_name: str | None = None,
) -> dict[str, Any]:
    """Roda a seleção de carteira (QUBO) numa QPU real. Trava explícita obrigatória.

    A decodificação repete o REPARO CLÁSSICO do caminho local: entre os estados
    amostrados pelo hardware, vale o melhor com exatamente K escolhas.
    """
    if not execution_gate_open():
        raise HardwareGateClosed(f"real QPU execution requires {EXECUTE_ENV_FLAG}=1 (explicit human approval)")
    _, generate_preset_pass_manager, QiskitRuntimeService, SamplerV2 = _require_qiskit()

    def objetivo(bits: tuple[int, ...]) -> float:
        return sum(coef for (i, j), coef in qubo.items() if bits[i] and bits[j])

    service = QiskitRuntimeService()
    backend = service.backend(backend_name) if backend_name else service.least_busy(operational=True, simulator=False)
    circuit = build_qubo_circuit(qubo, qubits, layers=layers)
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=1)
    transpiled = pass_manager.run(circuit)

    started = time.perf_counter()
    sampler = SamplerV2(mode=backend)
    job = sampler.run([transpiled], shots=shots)
    result = job.result()
    elapsed_ms = (time.perf_counter() - started) * 1_000

    counts = result[0].data.meas.get_counts()
    melhor_bits: tuple[int, ...] | None = None
    melhor_valor = math.inf
    melhor_geral: tuple[int, ...] | None = None
    melhor_geral_valor = math.inf
    for bitstring in counts:
        bits = tuple(int(bit) for bit in reversed(bitstring))
        valor = objetivo(bits)
        if valor < melhor_geral_valor:
            melhor_geral, melhor_geral_valor = bits, valor
        if sum(bits) == k and valor < melhor_valor:
            melhor_bits, melhor_valor = bits, valor
    reparado = melhor_bits is not None
    escolhido = melhor_bits if reparado else melhor_geral

    usage = getattr(job, "usage_estimation", None) or {}
    return {
        "solver": "selecao_carteira_qaoa",
        "backend": backend.name,
        "hardware_execution": True,
        "shots": shots,
        "layers": layers,
        "k": k,
        "circuit_depth_transpiled": transpiled.depth(),
        "execution_time_ms": elapsed_ms,
        "quantum_seconds_estimated": usage.get("quantum_seconds"),
        "solution": list(escolhido) if escolhido else None,
        "objetivo": melhor_valor if reparado else melhor_geral_valor,
        "reparo_com_k": reparado,
        "distinct_bitstrings": len(counts),
        "job_id": job.job_id(),
    }


def run_on_hardware(
    problem: BenchmarkProblem,
    layers: int = 2,
    shots: int = 1_024,
    backend_name: str | None = None,
) -> dict[str, Any]:
    """Submit the QAOA circuit to a real IBM QPU. Gate must be explicitly open."""
    if not execution_gate_open():
        raise HardwareGateClosed(f"real QPU execution requires {EXECUTE_ENV_FLAG}=1 (explicit human approval)")
    _, generate_preset_pass_manager, QiskitRuntimeService, SamplerV2 = _require_qiskit()

    service = QiskitRuntimeService()
    backend = service.backend(backend_name) if backend_name else service.least_busy(operational=True, simulator=False)
    circuit = build_qaoa_circuit(problem, layers=layers)
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=1)
    transpiled = pass_manager.run(circuit)

    started = time.perf_counter()
    sampler = SamplerV2(mode=backend)
    job = sampler.run([transpiled], shots=shots)
    result = job.result()
    elapsed_ms = (time.perf_counter() - started) * 1_000

    counts = result[0].data.meas.get_counts()
    best_bits: tuple[int, ...] | None = None
    best_score = 0.0
    for bitstring, _count in counts.items():
        # Qiskit bitstrings are little-endian relative to qubit index.
        bits = tuple(int(bit) for bit in reversed(bitstring))
        score = problem.score(bits)
        if score > best_score:
            best_score, best_bits = score, bits

    usage = getattr(job, "usage_estimation", None) or {}
    return {
        "solver": "qaoa",
        "backend": backend.name,
        "hardware_execution": True,
        "shots": shots,
        "layers": layers,
        "circuit_depth_transpiled": transpiled.depth(),
        "execution_time_ms": elapsed_ms,
        "quantum_seconds_estimated": usage.get("quantum_seconds"),
        "score": best_score,
        "solution": list(best_bits) if best_bits else None,
        "distinct_bitstrings": len(counts),
        "job_id": job.job_id(),
    }
