# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes de integridade dos registries do source-graph.
Molde de tests/decision_context/test_taxonomy.py: contagens declaradas batem com
a realidade, referências resolvem, e o crosswalk pendente permanece vazio.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "source-graph"
SCHEMA_DIR = DATA_DIR
BLOCKED_CONNECTORS = {"openalex"}  # cobra desde fev/2026; AGENTS.md proíbe criar custos


def load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def test_nineteen_phase_c_categories() -> None:
    registry = load("source_categories.json")
    categories = registry["categories"]
    assert registry["category_count"] == len(categories) == 19
    ids = [c["category_id"] for c in categories]
    assert len(set(ids)) == 19


def test_person_categories_are_flagged_for_dpia() -> None:
    """Acadêmicos, praticantes, árbitros e autoridades são pessoas: L4."""
    categories = {c["category_id"]: c for c in load("source_categories.json")["categories"]}
    for category_id in (
        "academics-and-researchers",
        "practitioners",
        "arbitrators-and-mediators",
        "institutional-authorities",
    ):
        assert categories[category_id]["requires_dpia"] is True
        assert categories[category_id]["default_entity_type"] == "person"


def test_authority_tiers_mirror_agents_hierarchy() -> None:
    registry = load("authority_tiers.json")
    tiers = registry["tiers"]
    assert registry["tier_count"] == len(tiers) == 8
    assert [t["tier"] for t in tiers] == list(range(1, 9))


def test_every_connector_declares_license_terms_and_limits() -> None:
    for connector in load("connectors.json")["connectors"]:
        cid = connector["connector_id"]
        for field in ("license_id", "license_url", "terms_url", "access_basis"):
            assert connector.get(field), f"{cid}: {field} é obrigatório"
        assert connector["min_interval_seconds"] > 0, f"{cid}: intervalo mínimo obrigatório"
        assert connector["max_bytes"] > 0, f"{cid}: limite de tamanho obrigatório"
        assert connector["access_basis"] in {"robots", "api_terms"}, f"{cid}: base de acesso inválida"


def test_every_connector_declares_what_it_does_not_provide() -> None:
    """Declarar o limite é parte do registro — fonte sem limite declarado mente por omissão."""
    for connector in load("connectors.json")["connectors"]:
        assert connector.get("does_not_provide"), f"{connector['connector_id']}: does_not_provide não pode ser vazio"


def test_no_paid_or_keyed_connector_is_enabled() -> None:
    for connector in load("connectors.json")["connectors"]:
        if connector.get("requires_key") or connector["connector_id"] in BLOCKED_CONNECTORS:
            assert connector["enabled"] is False, (
                f"{connector['connector_id']}: exige chave/custo e não pode estar habilitado"
            )


def test_stage_one_enables_no_connector() -> None:
    """O Estágio 1 não toca a rede: nenhum conector habilitado."""
    assert all(not c["enabled"] for c in load("connectors.json")["connectors"])


def test_ranking_weights_sum_to_one() -> None:
    weights = load("ranking_weights.json")["weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_ranking_weights_reference_declared_components() -> None:
    schema = json.loads((SCHEMA_DIR / "ranking-entry.schema.json").read_text(encoding="utf-8"))
    declared = set(schema["properties"]["score_components"]["items"]["properties"]["component_id"]["enum"])
    assert set(load("ranking_weights.json")["weights"]) == declared


def test_sales_crosswalk_stays_honest_until_licensed() -> None:
    """O slot vazio honesto: sem fonte licenciada, nenhum número de vendas entra."""
    crosswalk = load("sales_data_crosswalk.json")
    assert crosswalk["status"] == "pending_licensed_source"
    assert crosswalk["mappings"] == []
    policy = crosswalk["policy"].lower()
    assert "never inferred" in policy
    assert "licensed" in policy
    assert crosswalk["what_would_unblock"]


def test_software_artifacts_declare_license_and_limits() -> None:
    registry = load("software_artifacts.json")
    artifacts = registry["artifacts"]
    assert registry["artifact_count"] == len(artifacts)
    ids = [a["artifact_id"] for a in artifacts]
    assert len(set(ids)) == len(ids)
    for artifact in artifacts:
        for field in ("license_id", "repo_url", "docs_url", "poc_status", "verification_status"):
            assert artifact.get(field), f"{artifact['artifact_id']}: {field} obrigatório"
        assert artifact["poc_status"] in {"production", "research", "experimental", "unknown"}
        assert "does_not_provide" in artifact


def test_artifacts_carry_a_verification_verdict() -> None:
    """Licença declarada não é licença verificada: o veredito vem da fonte primária."""
    valid = {"verified", "license_mismatch", "fetch_failed", "declared_unverified"}
    for artifact in load("software_artifacts.json")["artifacts"]:
        assert artifact["verification_status"] in valid


def test_verified_artifacts_carry_the_response_hash() -> None:
    """Verificado sem hash da resposta seria afirmação sem prova."""
    for artifact in load("software_artifacts.json")["artifacts"]:
        if artifact["verification_status"] == "verified":
            assert len(artifact.get("content_hash_sha256", "")) == 64
            assert artifact.get("verified_at")


def test_license_mismatch_goes_to_human_review_not_silent_fix() -> None:
    """Divergência com a fonte primária não é corrigida em silêncio."""
    for artifact in load("software_artifacts.json")["artifacts"]:
        if artifact["verification_status"] == "license_mismatch":
            assert artifact["human_review"]["status"] == "pending"
            assert artifact["license_observed"] != artifact["license_id"]


def test_production_status_requires_a_published_release() -> None:
    """Declarar maturidade de produção sem release não se sustenta."""
    for artifact in load("software_artifacts.json")["artifacts"]:
        if artifact.get("poc_downgraded_from") == "production":
            assert artifact["poc_status"] != "production"
            assert artifact["poc_note"]


def test_quantum_ml_artifacts_declare_the_honest_limitation() -> None:
    """QML ainda não supera modelos clássicos em previsão prática — está escrito."""
    artifacts = {a["artifact_id"]: a for a in load("software_artifacts.json")["artifacts"]}
    for artifact_id in ("qiskit-machine-learning", "pennylane"):
        assert artifact_id in artifacts
        assert artifacts[artifact_id]["poc_status"] == "research"
        assert artifacts[artifact_id]["does_not_provide"], f"{artifact_id} deve declarar o limite"


def test_communities_are_sources_not_people() -> None:
    registry = load("communities.json")
    communities = registry["communities"]
    assert registry["community_count"] == len(communities)
    ids = [c["community_id"] for c in communities]
    assert len(set(ids)) == len(ids)
    serialized = json.dumps(registry).lower()
    for forbidden in ("follower", "member_list", "engagement", "sentiment"):
        assert forbidden not in serialized, f"registro de comunidade não pode conter {forbidden}"
    for community in communities:
        assert community.get("official_url", "").startswith("http")
        assert community.get("topic_ids")


def test_private_groups_are_excluded_with_a_reason() -> None:
    exclusions = load("communities.json")["excluded_by_policy"]
    assert exclusions
    for exclusion in exclusions:
        assert exclusion["what"] and exclusion["why"]
