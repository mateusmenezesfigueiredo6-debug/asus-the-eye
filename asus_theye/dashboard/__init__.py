"""Benchmark dashboard integration."""

from .app import create_dashboard_app
from .benchmark import benchmark_page, register_benchmark_routes

__all__ = ["benchmark_page", "create_dashboard_app", "register_benchmark_routes"]
