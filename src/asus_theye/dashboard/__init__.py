# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Benchmark dashboard integration."""

from .app import create_dashboard_app
from .benchmark import benchmark_page, register_benchmark_routes
from .markets import markets_page, register_markets_routes
from .mercados import mercados_page, register_mercados_routes
from .mlops import mlops_page, register_mlops_routes
from .projeto import projeto_page, register_projeto_routes

__all__ = [
    "benchmark_page",
    "create_dashboard_app",
    "markets_page",
    "mlops_page",
    "projeto_page",
    "register_benchmark_routes",
    "register_markets_routes",
    "mercados_page",
    "mlops_page",
    "register_mercados_routes",
    "register_mlops_routes",
    "register_projeto_routes",
]
