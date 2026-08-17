"""Mercados preditivos — pergunta binária com prazo, resolvida contra fonte oficial.

Domínio da plataforma (não benchmark externo), registrado em
``data/domains/mercados_preditivos.json``. O ciclo tem três atos, um por módulo:

- :mod:`asus_theye.markets.claim` — a afirmação: pergunta binária, prazo,
  probabilidade e a fonte de resolução herdada da área.
- :mod:`asus_theye.markets.resolution` — liquidar contra a fonte oficial (e só
  ela); Kalshi entra apenas como comparador de divergência.
- :mod:`asus_theye.markets.scoring` — Brier e skill contra baseline, com a
  janela sempre declarada e o baseline-vence publicado.

Emitir mercado não prova nada; liquidar contra fonte é o que separa previsão de
palpite.
"""

from __future__ import annotations

from asus_theye.markets.claim import (
    MarketClaim,
    MarketClaimError,
    load_areas,
    load_classifier,
    make_claim,
    resolution_source_for,
)
from asus_theye.markets.duckdb_source import (
    DB_ENV,
    MarketsSourceError,
    SettledContract,
    load_settled,
    produto_to_area,
    reconcile,
    recover_probability,
    resolve_db_path,
)
from asus_theye.markets.resolution import (
    ComparatorDivergence,
    Resolution,
    ResolutionError,
    record_comparator,
    resolve,
)
from asus_theye.markets.scoring import (
    ScoringError,
    base_rate,
    brier_score,
    skill_score,
)

__all__ = [
    "DB_ENV",
    "ComparatorDivergence",
    "MarketClaim",
    "MarketClaimError",
    "MarketsSourceError",
    "Resolution",
    "ResolutionError",
    "ScoringError",
    "SettledContract",
    "base_rate",
    "brier_score",
    "load_areas",
    "load_classifier",
    "load_settled",
    "make_claim",
    "produto_to_area",
    "recover_probability",
    "reconcile",
    "record_comparator",
    "resolution_source_for",
    "resolve",
    "resolve_db_path",
    "skill_score",
]
