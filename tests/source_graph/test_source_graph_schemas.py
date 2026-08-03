"""Testes de integridade dos schemas do source-graph.

Molde de tests/decision_context/test_schemas.py: a política vira estrutura, e o
teste trava a estrutura. Se alguém acrescentar um campo de seguidores, de
engajamento ou de predição sobre pessoa, o build quebra.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "data" / "source-graph"

EXPECTED_SCHEMAS = {
    "knowledge-source.schema.json",
    "ranking-entry.schema.json",
    "ranking-list.schema.json",
    "discovery-query.schema.json",
    "coverage-report.schema.json",
}

# Os 20 fragmentos já proibidos em decision-context, mais os 7 específicos de
# ranking de fontes: nenhuma métrica social pode virar componente de score.
PROHIBITED_FRAGMENTS = (
    "politic", "ideolog", "religio", "health", "race", "ethnic", "sexual",
    "biometric", "private_address", "family", "friendship", "geolocation",
    "psycholog", "sentiment", "corruption", "moral_score", "bias_score",
    "partiality", "prediction", "will_decide",
    "follower", "subscriber", "likes", "engagement", "virality", "reach",
    "popularity", "influence_score", "clout",
)

# Os 11 campos que a Phase C exige de toda entrada ranqueada (MISSION:254-256).
PHASE_C_REQUIRED = (
    "score_components", "evidence", "confidence", "methodology_version",
    "source_ids", "cut_off_date", "validation_date", "limitations",
    "conflicts_of_interest", "human_review", "score",
)

SCORE_COMPONENTS = {
    "authority_tier",
    "subarea_specialization",
    "documented_impact",
    "recency_continuity",
    "methodology_transparency",
    "structured_data_accessibility",
    "jurisdictional_relevance",
}


def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def iter_property_names(node: object):
    """Todo nome de propriedade declarado em qualquer nível da árvore."""
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            yield from properties.keys()
        for value in node.values():
            yield from iter_property_names(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_property_names(item)


def test_all_expected_schemas_exist_and_parse() -> None:
    present = {p.name for p in SCHEMA_DIR.glob("*.schema.json")}
    assert present == EXPECTED_SCHEMAS
    for name in EXPECTED_SCHEMAS:
        assert isinstance(load(name), dict)


@pytest.mark.parametrize("name", sorted(EXPECTED_SCHEMAS))
def test_minimization_additional_properties_false(name: str) -> None:
    assert load(name).get("additionalProperties") is False, (
        f"{name}: additionalProperties deve ser false (minimização estrutural)"
    )


@pytest.mark.parametrize("name", sorted(EXPECTED_SCHEMAS))
def test_no_prohibited_attribute_names(name: str) -> None:
    schema = load(name)
    for prop in iter_property_names(schema):
        lowered = prop.lower()
        for fragment in PROHIBITED_FRAGMENTS:
            assert fragment not in lowered, (
                f"{name}: propriedade {prop!r} casa fragmento proibido {fragment!r}"
            )


def test_ranking_entry_has_every_phase_c_field() -> None:
    required = set(load("ranking-entry.schema.json")["required"])
    for field in PHASE_C_REQUIRED:
        assert field in required, f"ranking-entry deve exigir {field} (Phase C)"


def test_score_components_are_a_closed_enum() -> None:
    """follower_count tem de LEVANTAR na validação, não ser ignorado."""
    schema = load("ranking-entry.schema.json")
    component = schema["properties"]["score_components"]["items"]["properties"]["component_id"]
    assert set(component["enum"]) == SCORE_COMPONENTS


def test_no_representation_for_absent_component_with_zero() -> None:
    """Componente ausente é omitido do array — não existe forma de declará-lo como 0."""
    items = load("ranking-entry.schema.json")["properties"]["score_components"]["items"]
    assert items["additionalProperties"] is False
    for field in ("component_id", "value", "evidence_ref", "claim_class", "computed_from"):
        assert field in items["required"], f"componente deve exigir {field}"


def test_denominator_travels_with_score() -> None:
    required = set(load("ranking-entry.schema.json")["required"])
    assert {"components_present", "components_declared"} <= required


def test_limitations_cannot_be_empty() -> None:
    """Se você não achou nenhuma limitação, você não olhou."""
    entry = load("ranking-entry.schema.json")
    assert entry["properties"]["limitations"]["minItems"] == 1


def test_ranking_list_cannot_declare_itself_padded() -> None:
    schema = load("ranking-list.schema.json")
    assert schema["properties"]["padded"]["const"] is False
    assert "qualified_count" in schema["required"]


def test_ranking_list_forbids_person_entity_type() -> None:
    """Ranking de pessoas é L4 e exige DPIA — não cabe numa lista publicável."""
    entity_types = set(load("ranking-list.schema.json")["properties"]["entity_type"]["enum"])
    assert "person" not in entity_types


def test_knowledge_source_manifest_requires_hash() -> None:
    manifest = load("knowledge-source.schema.json")["properties"]["source_manifest"]
    assert manifest["minItems"] == 1
    item = manifest["items"]
    assert item["properties"]["content_hash_sha256"]["pattern"] == "^[0-9a-f]{64}$"
    assert set(item["required"]) == {
        "source_id", "official_url", "retrieved_at", "content_hash_sha256"
    }


def test_knowledge_source_id_follows_agents_convention() -> None:
    """AGENTS.md:72 — fontes externas usam IDs como S001."""
    assert load("knowledge-source.schema.json")["properties"]["source_id"]["pattern"] == (
        "^S[0-9]{3,6}$"
    )


def test_production_poc_status_requires_evidence() -> None:
    """'production' sem evidência é marketing, não medição."""
    conditionals = load("knowledge-source.schema.json").get("allOf", [])
    assert any(
        clause.get("if", {}).get("properties", {}).get("poc_status", {}).get("const") == "production"
        and "evidence_ref" in clause.get("then", {}).get("required", [])
        for clause in conditionals
    )


@pytest.mark.parametrize(
    "name", ["knowledge-source.schema.json", "ranking-entry.schema.json", "ranking-list.schema.json"]
)
def test_human_review_is_mandatory(name: str) -> None:
    schema = load(name)
    assert schema["properties"]["human_review"]["properties"]["required"]["const"] is True
    assert "human_review" in schema["required"]


def test_every_coverage_zero_has_a_named_reason() -> None:
    """A diferença entre 'não temos' e 'não olhamos'."""
    schema = load("coverage-report.schema.json")
    expected = {
        "none", "no_free_source", "license_restricted", "robots_disallowed",
        "requires_paid_api", "requires_dpia", "not_yet_attempted",
    }
    for section in ("by_category", "by_niche", "gaps"):
        item = schema["properties"][section]["items"]
        assert "blocking_reason" in item["required"], f"{section} deve exigir blocking_reason"
        assert set(item["properties"]["blocking_reason"]["enum"]) == expected


def test_discovery_query_makes_coverage_reproducible() -> None:
    required = set(load("discovery-query.schema.json")["required"])
    assert {"connector_id", "query_string", "parameters", "executed_at",
            "response_hash_sha256", "robots_decision", "rate_limit_applied"} <= required
