# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public benchmark engine API."""

from .classical_benchmark import run_classical_benchmark
from .metrics import (
    calculate_qar,
    calculate_quality_gap,
    calculate_speed_ratio,
    calculate_stability,
    quality_gap,
    quantum_advantage_ratio,
    speed_ratio,
    stability_score,
)
from .qaoa_benchmark import run_qaoa_benchmark
from .qubo_benchmark import run_qubo_benchmark
from .runner import run_benchmark_suite
from .selecao_carteira import Candidato, candidatos_demo, selecionar_carteira

__all__ = [
    "Candidato",
    "calculate_quality_gap",
    "calculate_qar",
    "candidatos_demo",
    "selecionar_carteira",
    "calculate_speed_ratio",
    "calculate_stability",
    "quality_gap",
    "quantum_advantage_ratio",
    "run_benchmark_suite",
    "run_classical_benchmark",
    "run_qaoa_benchmark",
    "run_qubo_benchmark",
    "speed_ratio",
    "stability_score",
]
