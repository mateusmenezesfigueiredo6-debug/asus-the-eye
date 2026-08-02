"""Guardrail tests for the decision-context schemas (Phase G).

These tests make the LGPD/adjudicator-analytics policy structural: if a schema
ever gains a prohibited attribute, loses minimization, or weakens the conflict
state machine, the suite fails.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "data" / "decision-context"

EXPECTED_SCHEMAS = {
    "decision-makers.schema.json",
    "decision-bodies.schema.json",
    "assignment-rules.schema.json",
    "public-decisions.schema.json",
    "jurisprudential-patterns.schema.json",
    "panel-dynamics.schema.json",
    "conflict-alerts.schema.json",
    "institutional-context.schema.json",
    "metrics.schema.json",
    "data-protection.schema.json",
}

# Prohibited by AGENTS.md / master mission Phase G. No schema property name may
# contain any of these fragments.
PROHIBITED_FRAGMENTS = (
    "politic",
    "ideolog",
    "religio",
    "health",
    "race",
    "ethnic",
    "sexual",
    "biometric",
    "private_address",
    "family",
    "friendship",
    "geolocation",
    "psycholog",
    "sentiment",
    "corruption",
    "moral_score",
    "bias_score",
    "partiality",
    "prediction",
    "will_decide",
)

CONFLICT_STATES = {
    "no_public_indicator",
    "potential_indicator",
    "legal_review_required",
    "confirmed_by_official_decision",
    "resolved",
    "insufficient_information",
}

ADJUDICATOR_ROLES = {
    "judge",
    "appellate_judge",
    "justice",
    "rapporteur",
    "reviewer",
    "panel_member",
    "panel_president",
    "administrative_adjudicator",
    "regulatory_decision_maker",
    "tax_council_member",
    "audit_court_member",
    "arbitrator",
    "tribunal_president",
    "dispute_board_member",
    "sports_justice_member",
    "disciplinary_council_member",
}


def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def iter_property_names(node: object):
    """Yield every property name declared anywhere in a schema tree."""
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            yield from properties.keys()
        for value in node.values():
            yield from iter_property_names(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_property_names(item)


def test_all_expected_schemas_exist_and_parse():
    present = {p.name for p in SCHEMA_DIR.glob("*.schema.json")}
    assert present == EXPECTED_SCHEMAS
    for name in EXPECTED_SCHEMAS:
        assert isinstance(load(name), dict)


@pytest.mark.parametrize("name", sorted(EXPECTED_SCHEMAS))
def test_minimization_additional_properties_false(name: str):
    schema = load(name)
    assert schema.get("additionalProperties") is False, (
        f"{name}: top level must set additionalProperties false (data minimization)"
    )


@pytest.mark.parametrize("name", sorted(EXPECTED_SCHEMAS))
def test_no_prohibited_attribute_names(name: str):
    schema = load(name)
    for prop in iter_property_names(schema):
        lowered = prop.lower()
        for fragment in PROHIBITED_FRAGMENTS:
            assert fragment not in lowered, (
                f"{name}: property {prop!r} matches prohibited fragment {fragment!r}"
            )


def test_conflict_alert_state_machine_is_exact():
    schema = load("conflict-alerts.schema.json")
    states = set(schema["properties"]["state"]["enum"])
    assert states == CONFLICT_STATES
    # Confirmation requires an official decision reference.
    conditionals = schema.get("allOf", [])
    assert any(
        clause.get("if", {}).get("properties", {}).get("state", {}).get("const")
        == "confirmed_by_official_decision"
        and "official_decision_ref" in clause.get("then", {}).get("required", [])
        for clause in conditionals
    ), "confirmed_by_official_decision must require official_decision_ref"


def test_adjudicator_roles_exact_and_mediator_excluded():
    schema = load("decision-makers.schema.json")
    roles = set(schema["properties"]["role"]["enum"])
    assert roles == ADJUDICATOR_ROLES
    assert "mediator" not in roles


def test_metrics_require_denominator_and_uncertainty():
    schema = load("metrics.schema.json")
    required = set(schema["required"])
    for field in (
        "denominator",
        "period",
        "sample_size",
        "uncertainty",
        "missingness",
        "case_mix_controls",
        "unobserved_factors",
        "limitations",
    ):
        assert field in required, f"metrics.schema.json must require {field}"
    assert schema["properties"]["claim_class"]["const"] == "DERIVED_METRIC"


def test_pattern_claim_classes_and_no_prediction_language():
    schema = load("jurisprudential-patterns.schema.json")
    classes = set(schema["properties"]["claim_class"]["enum"])
    assert classes == {"FACT", "DERIVED_METRIC", "INFERENCE", "UNKNOWN", "PROHIBITED"}
    required = set(schema["required"])
    assert {"best_contrary_evidence", "limitations", "what_would_change_conclusion", "human_review"} <= required


@pytest.mark.parametrize(
    "name",
    ["decision-makers.schema.json", "jurisprudential-patterns.schema.json", "conflict-alerts.schema.json"],
)
def test_human_review_is_mandatory_on_person_referencing_records(name: str):
    schema = load(name)
    review = schema["properties"]["human_review"]
    assert review["properties"]["required"]["const"] is True
    assert "human_review" in schema["required"]


def test_data_protection_production_gate():
    schema = load("data-protection.schema.json")
    assert schema["properties"]["human_review_required"]["const"] is True
    gates = schema.get("allOf", [])
    assert any(
        clause.get("if", {}).get("properties", {}).get("approved_for_production", {}).get("const") is True
        and clause.get("then", {}).get("properties", {}).get("dpia_status", {}).get("const") == "approved"
        for clause in gates
    ), "approved_for_production must require an approved DPIA"
