"""Testes do score: as regras que impedem o número de mentir."""

from __future__ import annotations

import pytest

from asus_theye.source_graph.scoring import (
    ScoringError,
    build_ranking,
    load_weights,
    score_source,
)

SOURCE = {"source_id": "S001", "official_name": "Exemplo"}


def component(component_id: str, value: float) -> dict:
    return {
        "component_id": component_id,
        "value": value,
        "evidence_ref": "S001",
        "claim_class": "DERIVED_METRIC",
        "denominator": 100,
        "computed_from": "registros recuperados",
    }


def candidate(source_id: str, score_value: float, entity_type: str = "institution") -> dict:
    scored = score_source(
        {"source_id": source_id},
        [component("authority_tier", score_value), component("documented_impact", score_value)],
    )
    return {
        "source_id": source_id,
        "entity_type": entity_type,
        "scored": scored,
        "evidence": "manifesto hasheado",
        "source_ids": ["S001"],
    }


# --------------------------------------------------------------- sem imputação


def test_absent_component_is_omitted_not_zeroed() -> None:
    """A diferença que importa: omitir muda o score; zerar o distorce."""
    partial = score_source(SOURCE, [component("authority_tier", 1.0)])
    zero_filled = score_source(
        SOURCE,
        [component("authority_tier", 1.0)] + [component(cid, 0.0) for cid in load_weights() if cid != "authority_tier"],
    )
    assert partial["score"] == 1.0, "com um só componente presente, ele define o score"
    assert zero_filled["score"] < partial["score"], "zerar os ausentes rebaixaria o score"
    assert partial["score"] != zero_filled["score"]


def test_omitted_components_are_named_in_limitations() -> None:
    result = score_source(SOURCE, [component("authority_tier", 0.8)])
    text = " ".join(result["limitations"])
    assert "omitido, não zerado" in text
    assert "documented_impact" in text


# ---------------------------------------------------------- denominador visível


def test_present_and_declared_travel_with_the_score() -> None:
    result = score_source(SOURCE, [component("authority_tier", 0.9), component("recency_continuity", 0.5)])
    assert result["components_present"] == 2
    assert result["components_declared"] == 7
    assert "2 de 7" in " ".join(result["limitations"])


def test_confidence_degrades_with_coverage() -> None:
    full = score_source(SOURCE, [component(cid, 0.8) for cid in load_weights()])
    sparse = score_source(SOURCE, [component("authority_tier", 0.8)])
    assert full["confidence"] == "high"
    assert sparse["confidence"] == "insufficient"


# ------------------------------------------------------------------- validação


def test_social_metric_component_raises_instead_of_being_ignored() -> None:
    with pytest.raises(ScoringError, match="desconhecido"):
        score_source(SOURCE, [component("follower_count", 0.9)])


def test_value_outside_unit_interval_raises() -> None:
    with pytest.raises(ScoringError, match=r"\[0,1\]"):
        score_source(SOURCE, [component("authority_tier", 1.5)])


def test_component_without_evidence_raises() -> None:
    broken = component("authority_tier", 0.5)
    broken["evidence_ref"] = ""
    with pytest.raises(ScoringError, match="evidence_ref"):
        score_source(SOURCE, [broken])


def test_no_components_raises() -> None:
    with pytest.raises(ScoringError, match="nenhum componente"):
        score_source(SOURCE, [])


def test_duplicate_component_raises() -> None:
    with pytest.raises(ScoringError, match="duplicado"):
        score_source(SOURCE, [component("authority_tier", 0.5), component("authority_tier", 0.9)])


def test_scoring_is_deterministic() -> None:
    args = [component("authority_tier", 0.7), component("documented_impact", 0.3)]
    assert score_source(SOURCE, args)["score"] == score_source(SOURCE, args)["score"]


def test_methodology_version_is_stamped() -> None:
    result = score_source(SOURCE, [component("authority_tier", 0.5)])
    assert result["methodology_version"]


# --------------------------------------------------------------- sem preencher


def test_ranking_never_pads_to_target() -> None:
    result = build_ranking(
        [candidate(f"S{i:03d}", 0.5 + i / 100) for i in range(1, 8)],
        list_id="L001",
        list_scope="global",
        entity_type="institution",
        category_id="universities",
        target_size=100,
        cut_off_date="2026-08-02",
    )
    assert len(result["entries"]) == 7
    assert result["list"]["qualified_count"] == 7
    assert result["list"]["padded"] is False
    assert "não é preenchida artificialmente" in result["list"]["coverage_note"]


def test_ranking_is_ordered_by_score() -> None:
    result = build_ranking(
        [candidate("S001", 0.3), candidate("S002", 0.9), candidate("S003", 0.6)],
        list_id="L001",
        list_scope="global",
        entity_type="institution",
        category_id="universities",
        target_size=10,
        cut_off_date="2026-08-02",
    )
    assert [e["source_id"] for e in result["entries"]] == ["S002", "S003", "S001"]
    assert [e["rank"] for e in result["entries"]] == [1, 2, 3]


def test_ranking_people_is_refused() -> None:
    with pytest.raises(ScoringError, match="L4"):
        build_ranking(
            [],
            list_id="L001",
            list_scope="academic",
            entity_type="person",
            category_id="academics-and-researchers",
            target_size=100,
            cut_off_date="2026-08-02",
        )


def test_person_candidate_in_a_non_person_list_is_refused() -> None:
    with pytest.raises(ScoringError, match="person"):
        build_ranking(
            [candidate("S001", 0.5, entity_type="person")],
            list_id="L001",
            list_scope="global",
            entity_type="institution",
            category_id="universities",
            target_size=10,
            cut_off_date="2026-08-02",
        )


def test_mixed_entity_types_are_refused() -> None:
    with pytest.raises(ScoringError, match="misturar"):
        build_ranking(
            [candidate("S001", 0.5, entity_type="institution"), candidate("S002", 0.5, entity_type="journal")],
            list_id="L001",
            list_scope="global",
            entity_type="institution",
            category_id="universities",
            target_size=10,
            cut_off_date="2026-08-02",
        )


def test_every_entry_requires_human_review() -> None:
    result = build_ranking(
        [candidate("S001", 0.5)],
        list_id="L001",
        list_scope="global",
        entity_type="institution",
        category_id="universities",
        target_size=10,
        cut_off_date="2026-08-02",
    )
    for entry in result["entries"]:
        assert entry["human_review"] == {"required": True, "status": "pending"}
        assert entry["limitations"], "toda entrada tem ao menos uma limitação"
