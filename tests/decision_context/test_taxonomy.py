"""Integrity tests for the legal taxonomy registry."""

from __future__ import annotations

import json
from pathlib import Path

TAXONOMY_DIR = Path(__file__).resolve().parents[2] / "data" / "legal-taxonomy"


def load(name: str) -> dict:
    return json.loads((TAXONOMY_DIR / name).read_text(encoding="utf-8"))


def test_master_has_145_unique_areas() -> None:
    master = load("legal_areas.master.json")
    areas = master["areas"]
    assert master["area_count"] == len(areas) == 145
    ids = [a["legal_area_id"] for a in areas]
    assert len(set(ids)) == 145
    numbers = [a["number"] for a in areas]
    assert numbers == list(range(1, 146))


def test_every_area_belongs_to_exactly_one_group() -> None:
    master = load("legal_areas.master.json")
    relationships = load("legal_area_relationships.json")
    grouped = [area_id for members in relationships["groups"].values() for area_id in members]
    assert sorted(grouped) == sorted(a["legal_area_id"] for a in master["areas"])


def test_aliases_reference_real_areas() -> None:
    master_ids = {a["legal_area_id"] for a in load("legal_areas.master.json")["areas"]}
    aliases = load("legal_area_aliases.json")["aliases"]
    unknown = set(aliases) - master_ids
    assert not unknown, f"aliases point to unknown areas: {unknown}"


def test_crosswalks_stay_honest_until_official() -> None:
    for name in ("cnj_crosswalk.json", "international_crosswalk.json"):
        crosswalk = load(name)
        if crosswalk["status"] == "pending_official_mapping":
            assert crosswalk["mappings"] == [], f"{name}: pending crosswalk must have no mappings"
        assert "never" in crosswalk["policy"].lower() or "official" in crosswalk["policy"].lower()


def test_suggest_legal_areas_matches_and_stays_silent() -> None:
    from asus_theye.decision_context.legal_areas import suggest_legal_areas

    text = "Apelacao sobre contrato de consumo; aplica-se o CDC e o processo civil."
    suggested = suggest_legal_areas(text)
    assert "consumer" in suggested
    assert "civil-procedure" in suggested
    assert suggest_legal_areas("texto sem materia identificavel") == []


def test_suggest_respects_word_boundaries() -> None:
    from asus_theye.decision_context.legal_areas import suggest_legal_areas

    # "ia" must not fire inside other words like "materia" or "familia".
    assert "artificial-intelligence" not in suggest_legal_areas("materia da familia")
