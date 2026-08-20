# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plataforma comercial — um sistema, N nichos por configuração.

Nicho é dado, não código: acrescentar o 16º é uma entrada em
``data/commercial/niches.json``, não um repositório novo. É a mesma decisão que
fez os 145 nichos jurídicos funcionarem com um único classificador.
"""

from asus_theye.commercial.metrics import (
    MINIMUM_SAMPLE,
    TICKET_BANDS_BRL,
    compute_metrics,
    observed_band,
    rank_niches,
    reality_check,
)
from asus_theye.commercial.niches import (
    NicheError,
    load_niches,
    niche_by_id,
    niche_for_legal_areas,
)
from asus_theye.commercial.pipeline import (
    STAGES,
    OpportunityError,
    Pipeline,
    new_opportunity,
)

__all__ = [
    "MINIMUM_SAMPLE",
    "TICKET_BANDS_BRL",
    "STAGES",
    "NicheError",
    "OpportunityError",
    "Pipeline",
    "compute_metrics",
    "load_niches",
    "new_opportunity",
    "observed_band",
    "niche_by_id",
    "niche_for_legal_areas",
    "rank_niches",
    "reality_check",
]
