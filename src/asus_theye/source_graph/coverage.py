"""Cobertura real — e o motivo nomeado de cada zero.

A diferença que este módulo protege é entre "não temos" e "não olhamos".
``blocking_reason`` é enum fechado no schema: um zero sem motivo não valida.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asus_theye.source_graph.events import snapshot_hash

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "source-graph"
TAXONOMY_PATH = Path(__file__).resolve().parents[3] / "data" / "legal-taxonomy" / "legal_areas.master.json"

REPORT_VERSION = "1.0.0"

# Trilhas de trabalho: como as 19 categorias da Phase C se agrupam para navegação.
TRACKS: dict[str, tuple[str, ...]] = {
    "fundacao": (
        "journals-repositories-and-working-papers",
        "official-datasets-and-apis",
        "associations-and-think-tanks",
        "conferences-and-research-programs",
    ),
    "academico": (
        "universities",
        "schools-and-departments",
        "research-centers",
        "legal-clinics",
        "observatories",
    ),
    "setorial": (
        "regulators-and-public-bodies",
        "courts-and-tribunals",
        "arbitration-and-mediation-institutions",
        "sports-tribunals-and-federations",
        "law-firms-and-boutiques",
        "news-portals-newsletters-and-podcasts",
    ),
    "gated_dpia": (
        "academics-and-researchers",
        "practitioners",
        "arbitrators-and-mediators",
        "institutional-authorities",
    ),
}


def _load(name: str, directory: Path = DATA_DIR) -> dict:
    return json.loads((directory / name).read_text(encoding="utf-8"))


def track_for(category_id: str) -> str:
    for track, categories in TRACKS.items():
        if category_id in categories:
            return track
    return "outros"


def _blocking_reason(category: dict[str, Any], qualified: int) -> str:
    if qualified > 0:
        return "none"
    if category.get("requires_dpia"):
        return "requires_dpia"
    return "not_yet_attempted"


def build_coverage(
    sources: list[dict[str, Any]] | None = None,
    *,
    methodology_version: str = "1.0.0",
) -> dict[str, Any]:
    """Cobertura por categoria e por nicho, com motivo nomeado em cada zero."""
    sources = sources or []
    categories = _load("source_categories.json")["categories"]
    areas = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))["areas"]

    counted: dict[str, int] = {}
    by_niche_count: dict[str, int] = {}
    for source in sources:
        counted[source["category_id"]] = counted.get(source["category_id"], 0) + 1
        for area_id in source.get("legal_area_ids_suggested", []):
            by_niche_count[area_id] = by_niche_count.get(area_id, 0) + 1

    by_category = []
    for category in categories:
        qualified = counted.get(category["category_id"], 0)
        target = 100  # a Phase C fala em "até 100 entidades qualificadas"
        by_category.append(
            {
                "category_id": category["category_id"],
                "qualified_count": qualified,
                "target_size": target,
                "coverage_pct": round(100 * qualified / target, 2),
                "blocking_reason": _blocking_reason(category, qualified),
            }
        )

    by_niche = [
        {
            "legal_area_id": area["legal_area_id"],
            "qualified_count": by_niche_count.get(area["legal_area_id"], 0),
            "blocking_reason": "none" if by_niche_count.get(area["legal_area_id"]) else "not_yet_attempted",
        }
        for area in areas
    ]

    gaps = _known_gaps()

    report = {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "methodology_version": methodology_version,
        "by_category": by_category,
        "by_niche": by_niche,
        "gaps": gaps,
    }
    stable = {k: v for k, v in report.items() if k != "generated_at"}
    report["snapshot_hash_sha256"] = snapshot_hash(stable)
    return report


def _known_gaps() -> list[dict[str, str]]:
    """Lacunas conhecidas, cada uma com motivo e o que a destravaria."""
    return [
        {
            "description": "Volume de vendas de livros e tamanho de mercado por nicho",
            "blocking_reason": "requires_paid_api",
            "what_would_unblock": "Assinatura de Circana BookScan ou Nielsen BookData",
        },
        {
            "description": "Produção científica em escala para ranquear universidades",
            "blocking_reason": "requires_paid_api",
            "what_would_unblock": "Ingestão do dump CC0 do OpenAlex no S3 (grátis, sem chave)",
        },
        {
            "description": "Ranking de acadêmicos, praticantes e árbitros",
            "category_id": "academics-and-researchers",
            "blocking_reason": "requires_dpia",
            "what_would_unblock": "RIPD/DPIA concluída por profissional humano + aprovação de DPO/jurídico",
        },
        {
            "description": "Algoritmos proprietários de recomendação de plataformas sociais",
            "blocking_reason": "no_free_source",
            "what_would_unblock": (
                "Nada: não são públicos. O indexável são as publicações dessas "
                "empresas e as divulgações obrigatórias do art. 40 do DSA"
            ),
        },
        {
            "description": "Qualquer categoria — nenhum conector foi executado ainda",
            "blocking_reason": "not_yet_attempted",
            "what_would_unblock": "Estágio 2: habilitar conectores e executar a primeira corrida limitada",
        },
    ]


def coverage_by_track(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Agrega a cobertura por trilha — é o que o painel de navegação mostra."""
    tracks: dict[str, dict[str, Any]] = {}
    for entry in report["by_category"]:
        track = track_for(entry["category_id"])
        bucket = tracks.setdefault(track, {"categories": 0, "qualified": 0, "target": 0, "blocking_reasons": {}})
        bucket["categories"] += 1
        bucket["qualified"] += entry["qualified_count"]
        bucket["target"] += entry["target_size"]
        reason = entry["blocking_reason"]
        bucket["blocking_reasons"][reason] = bucket["blocking_reasons"].get(reason, 0) + 1
    for bucket in tracks.values():
        bucket["coverage_pct"] = round(100 * bucket["qualified"] / bucket["target"], 2) if bucket["target"] else 0.0
    return dict(sorted(tracks.items()))
