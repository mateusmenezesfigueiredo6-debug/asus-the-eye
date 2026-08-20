# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Optional standalone FastAPI application factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .api_docs import register_api_docs_routes
from .auth import registrar_auth
from .benchmark import register_benchmark_routes
from .evidencia import register_evidencia_routes
from .markets import register_markets_routes
from .mercados import register_mercados_routes
from .mlops import register_mlops_routes
from .projeto import register_projeto_routes


def create_dashboard_app(
    report_path: str | Path = "reports/benchmark/latest.json",
    markets_db: str | Path | None = None,
    *,
    require_auth: bool = False,
) -> Any:
    """Fábrica da app. ``require_auth=True`` exige token e recusa subir sem ele.

    Use ``require_auth=True`` sempre que a app for exposta fora de localhost
    (o comando ``asus-theye serve --expose`` já força isso).
    """
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to create the HTTP app") from exc

    app = FastAPI(title="ASUS THE EYE", version="0.2.0")
    registrar_auth(app, require=require_auth)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness: sempre livre (não expõe dado), usado pelos healthchecks."""
        return {"status": "ok"}

    register_benchmark_routes(app, report_path)
    register_markets_routes(app, markets_db)
    register_evidencia_routes(app)
    register_mlops_routes(app)
    register_projeto_routes(app)
    register_mercados_routes(app)
    register_api_docs_routes(app)
    return app
