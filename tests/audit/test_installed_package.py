# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testa que o pacote instalado (não-editável) consegue selar eventos.

O defeito original: ``sdk.py`` resolvia o caminho da migração via
``Path(__file__).parents[N]``, que só acerta no layout do repositório.
Instalado como pacote regular, esse caminho aponta para dentro de
``site-packages`` onde o arquivo não está, levantando ``FileNotFoundError``
e impedindo qualquer selagem.

Este teste comprova que a correção funciona em AMBOS os casos:
1. No repositório (editable install / dev): caminho via symlink.
2. Pacote instalado: caminho via ``importlib.resources``.
"""

from __future__ import annotations

import importlib.resources

from asus_theye.audit.schema import GENESIS_HASH, SCHEMA_VERSION, seal_event
from asus_theye.audit.sdk import SQLiteAuditStore


def test_migration_sql_legivel_via_importlib_resources() -> None:
    """O arquivo de migração deve ser legível independentemente do layout."""
    ref = importlib.resources.files("asus_theye").joinpath("migrations/0001_audit_ledger.sql")
    sql = ref.read_text(encoding="utf-8")
    assert "audit_events" in sql, "migração deve criar tabela audit_events"
    assert "CREATE TABLE IF NOT EXISTS audit_events" in sql


def test_sqliteauditstore_abre_sem_file_not_found_error() -> None:
    """SQLiteAuditStore não deve levantar FileNotFoundError na construção."""
    store = SQLiteAuditStore(":memory:")
    assert store.connection is not None


def test_selar_evento_com_store_em_memoria() -> None:
    """Selagem completa usando apenas o pacote instalado — sem deps do repo."""
    store = SQLiteAuditStore(":memory:")
    raw = {
        "schema_version": SCHEMA_VERSION,
        "event_id": "evt-instalado-01",
        "idempotency_key": "idem-instalado-01234567",
        "tenant_id": "tenant-test",
        "sequence": 1,
        "event_type": "document.created",
        "action": "create",
        "occurred_at": "2026-08-20T00:00:00Z",
        "recorded_at": "2026-08-20T00:00:01Z",
        "actor_type": "service",
        "actor_id_pseudonymous": "a" * 64,
        "actor_role": "writer",
        "source_system": "integration-test",
        "resource_type": "document",
        "resource_id_pseudonymous": "b" * 64,
        "resource_version": "1",
        "jurisdiction": "BR",
        "legal_area_ids": [],
        "classification": "restricted",
        "retention_policy_id": "audit-default-v1",
        "lawful_basis_reference": "test-only",
        "content_hash_sha256": "c" * 64,
        "metadata_hash_sha256": "d" * 64,
        "previous_event_hash_sha256": GENESIS_HASH,
        "correlation_id": "corr-01",
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
        "created_by_service": "integration-test",
        "build_version": "test",
    }
    sealed = seal_event(raw)
    receipt = store.append(sealed)
    assert "event_hash_sha256" in receipt
    event_hash = receipt["event_hash_sha256"]
    assert len(event_hash) == 64, "event_hash deve ser SHA-256 hex de 64 chars"
    # Imprime o hash como exigido pela prova no PR
    print(f"event_hash={event_hash}")
