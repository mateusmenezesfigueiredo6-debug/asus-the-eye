# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import copy
import json
import sqlite3

import pytest

from asus_theye.audit.batching import build_batch
from asus_theye.audit.canonical import CanonicalizationError, canonicalize
from asus_theye.audit.keccak import keccak256
from asus_theye.audit.manifest import build_manifest
from asus_theye.audit.merkle import MerkleTree, verify_proof
from asus_theye.audit.schema import GENESIS_HASH, SCHEMA_VERSION, seal_event, verify_chain, verify_event
from asus_theye.audit.sdk import AuditSDK, AuditUnavailableError, SQLiteAuditStore, redact
from asus_theye.audit.verifier import verify_document


def event(sequence: int, previous: str = GENESIS_HASH, *, tenant: str = "tenant-a"):
    body = {
        "schema_version": SCHEMA_VERSION,
        "event_id": f"event-{sequence}",
        "idempotency_key": f"idem-key-{sequence:016d}",
        "tenant_id": tenant,
        "sequence": sequence,
        "event_type": "document.updated",
        "action": "update",
        "occurred_at": "2026-08-02T00:00:00Z",
        "recorded_at": "2026-08-02T00:00:01Z",
        "actor_type": "user",
        "actor_id_pseudonymous": "1" * 64,
        "actor_role": "editor",
        "source_system": "test",
        "resource_type": "document",
        "resource_id_pseudonymous": "2" * 64,
        "resource_version": str(sequence),
        "jurisdiction": "BR",
        "legal_area_ids": ["civil"],
        "classification": "restricted",
        "retention_policy_id": "audit-default-v1",
        "lawful_basis_reference": "test-only",
        "content_hash_sha256": "3" * 64,
        "metadata_hash_sha256": "4" * 64,
        "previous_event_hash_sha256": previous,
        "correlation_id": "correlation-1",
        "causation_id": None,
        "model_provider": None,
        "model_name": None,
        "model_version": None,
        "prompt_template_version": None,
        "source_citation_hashes": [],
        "human_review_status": "not_required",
        "reviewer_pseudonymous": None,
        "result_status": "success",
        "error_code": None,
        "created_by_service": "test",
        "build_version": "test",
    }
    return seal_event(body)


def chain(count: int = 3):
    values, previous = [], GENESIS_HASH
    for sequence in range(1, count + 1):
        item = event(sequence, previous)
        values.append(item)
        previous = item["event_hash_sha256"]
    return values


def test_rfc8785_vectors_and_semantic_key_reordering():
    first = {"numbers": [333333333.3333333, 1e30, 4.5, 0.002, 1e-27], "a": "x"}
    second = {"a": "x", "numbers": [333333333.3333333, 1e30, 4.5, 0.002, 1e-27]}
    expected = '{"a":"x","numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27]}'
    assert canonicalize(first) == expected == canonicalize(second)
    assert canonicalize(-0.0) == "0"
    with pytest.raises(CanonicalizationError):
        canonicalize(float("nan"))


def test_keccak_is_ethereum_keccak_not_nist_sha3():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_byte_tamper_sequence_and_previous_hash_are_detected():
    values = chain()
    assert verify_chain(values)
    changed = copy.deepcopy(values)
    changed[1]["action"] = "delete"
    assert not verify_event(changed[1]) and not verify_chain(changed)
    reordered = copy.deepcopy(values)
    reordered[1]["sequence"] = 9
    assert not verify_chain(reordered)
    previous = copy.deepcopy(values)
    previous[2]["previous_event_hash_sha256"] = "f" * 64
    assert not verify_chain(previous)


def test_merkle_proofs_duplicates_and_golden_vector():
    values = chain()
    tree = MerkleTree(list(reversed(values)))
    assert tree.root == "d48851a5bbfe8101261ceb6399ca36f320325f2db119e89a0dfa1111752edca4"
    for index, item in enumerate(values):
        assert verify_proof(item["event_hash_sha256"], tree.proof(index))
    bad = tree.proof(0).__dict__ | {"siblings": ("00" * 32,) + tree.proof(0).siblings[1:]}
    assert not verify_proof(values[0]["event_hash_sha256"], bad)
    with pytest.raises(ValueError, match="duplicate"):
        MerkleTree(values + [values[0]])


def test_manifest_is_pre_anchor_and_hashes_all_fields():
    manifest = build_manifest(chain(), storage_reference="r2://opaque-batch-id")
    assert manifest["event_count"] == 3
    assert manifest["blockchain_tx_hash"] is None
    assert len(manifest["manifest_hash_sha256"]) == 64


def test_verifier_infere_e_valida_o_lote_emitido_pelo_batcher():
    batch = build_batch(chain())

    recibo = verify_document(batch)

    assert recibo["target_type"] == "batch"
    assert recibo["target_id"] == batch["manifest"]["batch_id"]
    assert recibo["checks"] == {"leaf_proof_root": True, "manifest_hash": True}
    assert recibo["status"] == "not_anchored"


def test_verifier_rejeita_documento_sem_kind_com_forma_ambigua():
    ambiguo = build_batch(chain()) | {"event": chain(1)[0]}

    with pytest.raises(ValueError, match="ambiguous verification document.*batch.*event"):
        verify_document(ambiguo)


def test_verifier_de_lote_rejeita_raiz_que_nao_e_a_do_manifesto():
    batch = build_batch(chain())
    batch["proofs"][0]["proof"]["root"] = "0" * 64

    recibo = verify_document(batch)

    assert recibo["checks"] == {"leaf_proof_root": False, "manifest_hash": True}
    assert recibo["status"] == "invalid"


def test_sdk_redaction_pseudonymization_idempotency_and_outbox():
    store = SQLiteAuditStore()
    sdk = AuditSDK(store, pseudonymization_key=b"local-test-key-32-bytes-long!!!!", service="test", build_version="1")
    values = dict(
        tenant_id="tenant-a",
        event_type="document.updated",
        action="update",
        correlation_id="corr",
        actor_id="alice@example.test",
        resource_id="doc-123",
        content={"text": "hashed", "password": "never"},
        metadata={"email": "never"},
        idempotency_key="stable-idempotency-key",
    )
    first = sdk.recordMutation(**values)
    second = sdk.recordMutation(**values)
    assert first["duplicate"] is False and second["duplicate"] is True
    assert store.connection.execute("SELECT count(*) FROM audit_events").fetchone()[0] == 1
    assert store.connection.execute("SELECT count(*) FROM audit_outbox").fetchone()[0] == 1
    assert redact({"password": "value", "safe": "ok"}) == {"password": "[REDACTED]", "safe": "ok"}
    stored = store.events("tenant-a")[0]
    assert "alice@example.test" not in json.dumps(stored)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        store.connection.execute("UPDATE audit_events SET event_type='x'")


def test_critical_mutation_fails_explicitly_when_store_is_unavailable():
    store = SQLiteAuditStore()
    sdk = AuditSDK(store, pseudonymization_key=b"local-test-key-32-bytes-long!!!!", service="test", build_version="1")
    store.connection.close()
    with pytest.raises(AuditUnavailableError):
        sdk.recordMutation(
            tenant_id="t", event_type="case.updated", action="update", correlation_id="c", actor_id="a", resource_id="r"
        )
