"""API do diretor comercial. Local, sem autenticação externa, nada publicado.

Serve o frontend estático e expõe o funil, as métricas e o classificador. Roda
em localhost — não é a superfície pública (essa é L5 e continua não construída).
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from asus_theye.commercial import (
    OpportunityError,
    Pipeline,
    compute_metrics,
    load_niches,
    new_opportunity,
    rank_niches,
)
from asus_theye.commercial.niches import NicheError, classify_case, niche_by_id

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_PIPELINE_PATH = Path(
    os.environ.get("THE_EYE_PIPELINE_PATH", "reports/commercial/pipeline.jsonl")
)


def _default_period() -> tuple[str, str]:
    today = date.today()
    return (today - timedelta(days=365)).isoformat(), today.isoformat()


def create_app(pipeline_path: Path | None = None) -> Any:
    try:
        from fastapi import Body, FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Instale o extra 'dashboard' (fastapi) para rodar a API") from exc

    pipeline = Pipeline(pipeline_path or DEFAULT_PIPELINE_PATH)
    app = FastAPI(title="THE EYE — Diretor Comercial", version="1.0.0")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "service": "comercial",
            "niches": len(load_niches()),
            "pipeline_path": str(pipeline.path),
            "published": False,
        }

    @app.get("/api/niches")
    def niches() -> dict[str, Any]:
        return {"niches": list(load_niches())}

    @app.get("/api/opportunities")
    def opportunities(niche_id: str | None = Query(None)) -> dict[str, Any]:
        items = pipeline.opportunities()
        if niche_id:
            items = [o for o in items if o["niche_id"] == niche_id]
        return {"opportunities": sorted(items, key=lambda o: o["updated_at"], reverse=True)}

    @app.post("/api/opportunities")
    def create_opportunity(body: dict[str, Any] = Body(...)) -> Any:
        try:
            niche_by_id(body["niche_id"])
            opportunity = new_opportunity(
                niche_id=body["niche_id"],
                client_identifier=body["client_identifier"],
                source_channel=body.get("source_channel", "outro"),
                client_type=body.get("client_type", "empresa"),
                legal_area_ids=body.get("legal_area_ids"),
                engagement_model=body.get("engagement_model"),
                notes=body.get("notes"),
            )
        except (KeyError, NicheError, OpportunityError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return pipeline.add(opportunity)

    @app.post("/api/opportunities/{opportunity_id}/advance")
    def advance(opportunity_id: str, body: dict[str, Any] = Body(...)) -> Any:
        try:
            return pipeline.advance(
                opportunity_id,
                body["to_stage"],
                lost_reason=body.get("lost_reason"),
                value_brl=body.get("value_brl"),
                probability_declared=body.get("probability_declared"),
            )
        except (KeyError, OpportunityError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/opportunities/{opportunity_id}/history")
    def history(opportunity_id: str) -> Any:
        try:
            return {"history": pipeline.history(opportunity_id)}
        except OpportunityError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/classify")
    def classify(body: dict[str, Any] = Body(...)) -> Any:
        text = body.get("text", "")
        if not text.strip():
            raise HTTPException(status_code=422, detail="texto vazio")
        return classify_case(text)

    @app.get("/api/metrics/{niche_id}")
    def metrics(niche_id: str) -> Any:
        start, end = _default_period()
        try:
            niche_by_id(niche_id)
        except NicheError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return compute_metrics(
            pipeline.opportunities(), niche_id, period_start=start, period_end=end
        )

    @app.get("/api/ranking")
    def ranking(by: str = Query("win_rate")) -> Any:
        start, end = _default_period()
        try:
            return rank_niches(
                pipeline.opportunities(),
                [n["niche_id"] for n in load_niches()],
                period_start=start,
                period_end=end,
                by=by,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/overview")
    def overview() -> Any:
        start, end = _default_period()
        items = pipeline.opportunities()
        all_metrics = [
            compute_metrics(items, n["niche_id"], period_start=start, period_end=end)
            for n in load_niches()
        ]
        revenues = [m["revenue_brl"] for m in all_metrics if m["revenue_brl"] is not None]
        closed = sum(m["denominator"] for m in all_metrics)
        won = sum(m["won"] for m in all_metrics)
        return {
            "period_start": start,
            "period_end": end,
            "niches": len(all_metrics),
            "opportunities_total": len(items),
            "open": sum(m["open"] for m in all_metrics),
            "won": won,
            "lost": sum(m["lost"] for m in all_metrics),
            "win_rate": round(won / closed, 4) if closed else None,
            "denominator": closed,
            "revenue_brl": round(sum(revenues), 2) if revenues else None,
            "niches_with_sufficient_sample": sum(1 for m in all_metrics if m["sample_sufficient"]),
            "metrics": all_metrics,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/")
        def index() -> Any:
            return FileResponse(STATIC_DIR / "index.html")

    return app
