"""Optional standalone FastAPI application factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .benchmark import register_benchmark_routes
from .markets import register_markets_routes


def create_dashboard_app(
    report_path: str | Path = "reports/benchmark/latest.json",
    markets_db: str | Path | None = None,
) -> Any:
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to create the HTTP app") from exc

    app = FastAPI(title="ASUS THE EYE", version="0.2.0")
    register_benchmark_routes(app, report_path)
    register_markets_routes(app, markets_db)
    return app
