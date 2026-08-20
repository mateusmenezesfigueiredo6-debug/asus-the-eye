# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Grafo de fontes de conhecimento (Phase C).

Descoberta, proveniência hasheada, classificação por nicho e ranking com
evidência — com cobertura honesta e o motivo nomeado de cada zero.
"""

from asus_theye.source_graph.coverage import build_coverage, coverage_by_track, track_for
from asus_theye.source_graph.events import (
    graph_built_event,
    ranking_published_event,
    snapshot_hash,
    source_snapshot_event,
)
from asus_theye.source_graph.fetcher import (
    FetchError,
    FetchPolicy,
    FetchRefusal,
    FetchResult,
    PoliteFetcher,
)
from asus_theye.source_graph.report import write_reports
from asus_theye.source_graph.scoring import ScoringError, build_ranking, score_source

__all__ = [
    "FetchError",
    "FetchPolicy",
    "FetchRefusal",
    "FetchResult",
    "PoliteFetcher",
    "ScoringError",
    "build_coverage",
    "build_ranking",
    "coverage_by_track",
    "graph_built_event",
    "ranking_published_event",
    "score_source",
    "snapshot_hash",
    "source_snapshot_event",
    "track_for",
    "write_reports",
]
