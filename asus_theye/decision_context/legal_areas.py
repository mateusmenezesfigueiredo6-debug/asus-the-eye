"""Suggest legal areas for a text using the taxonomy alias registry.

Deterministic substring matching over reviewed PT-BR aliases — no model, no
inference. A suggestion is a pointer for human review, tagged as such; texts
matching nothing get an empty list, never a guess.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

TAXONOMY_DIR = Path(__file__).resolve().parents[2] / "data" / "legal-taxonomy"


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped)


@lru_cache(maxsize=1)
def _alias_index() -> tuple[tuple[str, str], ...]:
    data = json.loads((TAXONOMY_DIR / "legal_area_aliases.json").read_text(encoding="utf-8"))
    pairs: list[tuple[str, str]] = []
    for area_id, aliases in data["aliases"].items():
        for alias in aliases:
            pairs.append((_normalize(alias), area_id))
    # Longest alias first so "processo penal" wins over "penal".
    return tuple(sorted(pairs, key=lambda item: -len(item[0])))


def suggest_legal_areas(text: str, limit: int = 5) -> list[str]:
    """Return up to ``limit`` legal_area_ids whose aliases appear in the text."""
    normalized = _normalize(text)
    found: list[str] = []
    for alias, area_id in _alias_index():
        if area_id in found:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", normalized):
            found.append(area_id)
            if len(found) >= limit:
                break
    return found
