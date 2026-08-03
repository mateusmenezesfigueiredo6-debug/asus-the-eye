"""Registro dos nichos comerciais e a ponte com a taxonomia de 145 áreas.

A ponte é o que faz o classificador jurídico servir ao comercial: um texto de
caso passa por ``suggest_legal_areas`` (145 áreas) e cai automaticamente no
nicho comercial correspondente, sem um segundo classificador.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "commercial" / "niches.json"
TAXONOMY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "legal-taxonomy" / "legal_areas.master.json"
)


class NicheError(RuntimeError):
    """Configuração de nicho inválida."""


@lru_cache(maxsize=1)
def load_niches() -> tuple[dict[str, Any], ...]:
    registry = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    niches = registry["niches"]
    if registry["niche_count"] != len(niches):
        raise NicheError(
            f"niche_count declara {registry['niche_count']} mas há {len(niches)} nichos"
        )
    ids = [n["niche_id"] for n in niches]
    if len(set(ids)) != len(ids):
        raise NicheError("niche_id duplicado")

    valid_areas = {
        area["legal_area_id"]
        for area in json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))["areas"]
    }
    for niche in niches:
        unknown = set(niche["legal_area_ids"]) - valid_areas
        if unknown:
            raise NicheError(f"{niche['niche_id']} referencia áreas inexistentes: {sorted(unknown)}")
    return tuple(niches)


def niche_by_id(niche_id: str) -> dict[str, Any]:
    for niche in load_niches():
        if niche["niche_id"] == niche_id:
            return niche
    raise NicheError(f"nicho desconhecido: {niche_id!r}")


@lru_cache(maxsize=1)
def _area_to_niche() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for niche in load_niches():
        for area_id in niche["legal_area_ids"]:
            # Uma área jurídica pertence a no máximo um nicho comercial; se dois
            # nichos a reivindicassem, a classificação seria ambígua.
            if area_id in mapping and mapping[area_id] != niche["niche_id"]:
                raise NicheError(
                    f"área {area_id!r} reivindicada por {mapping[area_id]!r} e {niche['niche_id']!r}"
                )
            mapping[area_id] = niche["niche_id"]
    return mapping


def niche_for_legal_areas(legal_area_ids: list[str]) -> str | None:
    """Nicho comercial a partir das áreas sugeridas pelo classificador jurídico.

    Devolve ``None`` quando nenhuma área mapeia — silêncio é resposta válida, e
    é melhor que empurrar a oportunidade para um nicho errado.
    """
    mapping = _area_to_niche()
    for area_id in legal_area_ids:
        if area_id in mapping:
            return mapping[area_id]
    return None


def classify_case(text: str) -> dict[str, Any]:
    """Classifica um texto de caso: áreas jurídicas + nicho comercial."""
    from asus_theye.decision_context.legal_areas import suggest_legal_areas

    areas = suggest_legal_areas(text)
    return {
        "legal_area_ids_suggested": areas,
        "niche_id": niche_for_legal_areas(areas),
        "claim_class": "DERIVED_METRIC" if areas else "UNKNOWN",
    }
