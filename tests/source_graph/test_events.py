"""Testes dos eventos e da cobertura.

O teste mais importante do arquivo é o primeiro: nenhum payload pode carregar
texto de conteúdo. O ledger guarda a prova de que algo foi buscado — nunca o que
foi buscado.
"""

from __future__ import annotations

import json

import pytest

from asus_theye.audit.sdk import SENSITIVE_KEYS
from asus_theye.source_graph.coverage import build_coverage, coverage_by_track, track_for
from asus_theye.source_graph.events import (
    graph_built_event,
    ranking_published_event,
    source_snapshot_event,
)
from asus_theye.source_graph.fetcher import FetchResult

RESULT = FetchResult(
    url="https://api.invalid/works?query=segredo-comercial",
    status=200,
    retrieved_at="2026-08-02T12:00:00Z",
    content_hash_sha256="ab" * 32,
    content_type="application/json",
    byte_length=4096,
    body=b'{"titulo":"Um titulo que jamais pode vazar","autor":"Fulano de Tal"}',
    license_id="CC0-1.0",
    robots_decision="api_terms:https://api.invalid/terms",
    connector_id="fake",
    retries=0,
    waited_seconds=3.0,
)

RANKING_LIST = {
    "list_id": "L001",
    "list_scope": "global",
    "entity_type": "journal",
    "category_id": "journals-repositories-and-working-papers",
    "methodology_version": "1.0.0",
    "qualified_count": 7,
    "target_size": 100,
    "padded": False,
    "cut_off_date": "2026-08-02",
}


def all_events() -> list[dict]:
    return [
        source_snapshot_event(RESULT, "S001"),
        graph_built_event({"sources_total": 3, "by_category": {"universities": 3}}, "abc1234"),
        ranking_published_event(RANKING_LIST),
    ]


# ---------------------------------------------------------- nada de conteúdo


@pytest.mark.parametrize("event", all_events())
def test_no_payload_key_is_sensitive(event: dict) -> None:
    """Nenhuma chave do payload pode ser sensível segundo o SDK de auditoria.

    Campos ``*_sha256`` são explicitamente permitidos: um hash de conteúdo é o
    oposto de conteúdo — é o que se publica NO LUGAR dele. (SENSITIVE_KEYS casa
    ``content_hash_sha256`` por prefixo, um falso positivo do regex.)
    """
    for key in event["payload"]:
        if key.endswith("_sha256"):
            continue
        assert not SENSITIVE_KEYS.search(key), f"chave sensível no payload: {key}"


def test_response_body_never_reaches_the_ledger() -> None:
    serialized = json.dumps(all_events())
    assert "Um titulo que jamais pode vazar" not in serialized
    assert "Fulano de Tal" not in serialized
    assert "segredo-comercial" not in serialized, "nem a query vai — só o host"


def test_payload_values_are_short_enough_to_not_be_content() -> None:
    """Proxy para 'não há texto de conteúdo aqui': nenhum valor longo."""
    for event in all_events():
        for key, value in event["payload"].items():
            if isinstance(value, str):
                assert len(value) <= 256, f"{key} longo demais para ser metadado"


def test_only_the_host_is_recorded_not_the_full_url() -> None:
    payload = source_snapshot_event(RESULT, "S001")["payload"]
    assert payload["host"] == "api.invalid"
    assert "url" not in payload


# ------------------------------------------------------------- idempotência


def test_idempotency_keys_derive_from_hash_and_are_stable() -> None:
    first, second = source_snapshot_event(RESULT, "S001"), source_snapshot_event(RESULT, "S001")
    assert first["idempotency_key"] == second["idempotency_key"]
    assert first["idempotency_key"].startswith("srcgraph-")


def test_event_types_are_the_three_declared() -> None:
    types = {event["event_type"] for event in all_events()}
    assert types == {"source.snapshot.recorded", "source.graph.built", "ranking.published"}


def test_access_basis_is_recorded_in_the_event() -> None:
    """A base da autorização viaja com a evidência, nunca fica implícita."""
    payload = source_snapshot_event(RESULT, "S001")["payload"]
    assert payload["robots_decision"] == "api_terms:https://api.invalid/terms"
    assert payload["license_id"] == "CC0-1.0"


# ------------------------------------------------------------------ cobertura


def test_empty_coverage_names_the_reason_for_every_zero() -> None:
    report = build_coverage([])
    assert report["by_category"]
    for entry in report["by_category"]:
        assert entry["qualified_count"] == 0
        assert entry["blocking_reason"] != "none", "zero sem motivo nomeado é inaceitável"


def test_person_categories_are_blocked_by_dpia_not_by_omission() -> None:
    report = build_coverage([])
    reasons = {e["category_id"]: e["blocking_reason"] for e in report["by_category"]}
    assert reasons["academics-and-researchers"] == "requires_dpia"
    assert reasons["universities"] == "not_yet_attempted"


def test_coverage_counts_real_sources() -> None:
    report = build_coverage(
        [
            {"category_id": "universities", "legal_area_ids_suggested": ["artificial-intelligence"]},
            {"category_id": "universities", "legal_area_ids_suggested": []},
        ]
    )
    by_category = {e["category_id"]: e for e in report["by_category"]}
    assert by_category["universities"]["qualified_count"] == 2
    assert by_category["universities"]["blocking_reason"] == "none"
    by_niche = {e["legal_area_id"]: e for e in report["by_niche"]}
    assert by_niche["artificial-intelligence"]["qualified_count"] == 1


def test_all_145_niches_appear_in_coverage() -> None:
    assert len(build_coverage([])["by_niche"]) == 145


def test_gaps_each_name_what_would_unblock() -> None:
    for gap in build_coverage([])["gaps"]:
        assert gap["description"] and gap["blocking_reason"]
        assert gap.get("what_would_unblock"), f"lacuna sem saída declarada: {gap['description']}"


def test_tracks_partition_the_categories() -> None:
    report = build_coverage([])
    tracks = coverage_by_track(report)
    assert set(tracks) >= {"fundacao", "academico", "setorial", "gated_dpia"}
    assert sum(t["categories"] for t in tracks.values()) == 19
    assert track_for("universities") == "academico"
    assert track_for("practitioners") == "gated_dpia"


def test_coverage_snapshot_hash_is_deterministic() -> None:
    first = build_coverage([])["snapshot_hash_sha256"]
    second = build_coverage([])["snapshot_hash_sha256"]
    assert first == second, "o hash ignora generated_at — duas execuções iguais batem"
