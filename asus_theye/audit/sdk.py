"""Single privacy-aware Audit SDK and transactional SQLite adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical import canonicalize
from .schema import GENESIS_HASH, SCHEMA_VERSION, hash_json, seal_event, verify_event

SENSITIVE_KEYS = re.compile(
    r"(^|_)(password|secret|token|authorization|cookie|cpf|cnpj|email|phone|address|prompt|response|content)(_|$)",
    re.IGNORECASE,
)


class AuditUnavailableError(RuntimeError):
    """A critical mutation could not produce durable audit evidence."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if SENSITIVE_KEYS.search(key) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class SQLiteAuditStore:
    """Local reference store. Production adapters must preserve identical invariants."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        migration = Path(__file__).parents[2] / "migrations" / "0001_audit_ledger.sql"
        self.connection.executescript(migration.read_text(encoding="utf-8"))

    def next_position(self, tenant_id: str) -> tuple[int, str]:
        row = self.connection.execute(
            "SELECT sequence, event_hash_sha256 FROM audit_events WHERE tenant_id=? ORDER BY sequence DESC LIMIT 1",
            (tenant_id,),
        ).fetchone()
        return (int(row[0]) + 1, row[1]) if row else (1, GENESIS_HASH)

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        if not verify_event(event):
            raise ValueError("invalid sealed audit event")
        receipt_id = str(uuid.uuid4())
        serialized = canonicalize(event)
        try:
            with self.connection:
                expected_sequence, previous = self.next_position(event["tenant_id"])
                if event["sequence"] != expected_sequence or event["previous_event_hash_sha256"] != previous:
                    raise ValueError("tenant sequence/hash chain conflict")
                self.connection.execute(
                    """INSERT INTO audit_events
                       (event_id,tenant_id,sequence,idempotency_key,event_type,resource_type,
                        resource_id_pseudonymous,recorded_at,event_hash_sha256,
                        previous_event_hash_sha256,event_json)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (event["event_id"], event["tenant_id"], event["sequence"], event["idempotency_key"],
                     event["event_type"], event["resource_type"], event["resource_id_pseudonymous"],
                     event["recorded_at"], event["event_hash_sha256"],
                     event["previous_event_hash_sha256"], serialized),
                )
                self.connection.execute(
                    "INSERT INTO audit_outbox (outbox_id,event_id,tenant_id,payload,status,attempts,available_at)"
                    " VALUES (?,?,?,?, 'pending',0,?)",
                    (receipt_id, event["event_id"], event["tenant_id"], serialized, event["recorded_at"]),
                )
        except sqlite3.IntegrityError as exc:
            existing = self.connection.execute(
                "SELECT event_id,event_hash_sha256 FROM audit_events WHERE tenant_id=? AND idempotency_key=?",
                (event["tenant_id"], event["idempotency_key"]),
            ).fetchone()
            if existing:
                return {
                    "receipt_id": receipt_id, "event_id": existing[0],
                    "event_hash_sha256": existing[1], "duplicate": True,
                }
            raise ValueError("audit uniqueness invariant violated") from exc
        return {
            "receipt_id": receipt_id, "event_id": event["event_id"],
            "event_hash_sha256": event["event_hash_sha256"], "duplicate": False,
        }

    def events(self, tenant_id: str, resource_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT event_json FROM audit_events WHERE tenant_id=?"
        values: list[Any] = [tenant_id]
        if resource_id is not None:
            query += " AND resource_id_pseudonymous=?"
            values.append(resource_id)
        query += " ORDER BY sequence"
        return [json.loads(row[0]) for row in self.connection.execute(query, values)]


class AuditSDK:
    def __init__(
        self, store: SQLiteAuditStore, *, pseudonymization_key: bytes, service: str, build_version: str
    ) -> None:
        if len(pseudonymization_key) < 16:
            raise ValueError("pseudonymization key must contain at least 128 bits")
        self.store = store
        self.key = pseudonymization_key
        self.service = service
        self.build_version = build_version

    def pseudonymize(self, identifier: str, tenant_id: str) -> str:
        return hmac.new(self.key, f"{tenant_id}\0{identifier}".encode(), hashlib.sha256).hexdigest()

    def record(self, *, tenant_id: str, event_type: str, action: str, correlation_id: str,
               actor_id: str, resource_id: str, content: Any = None, metadata: Any = None,
               critical: bool = False, **values: Any) -> dict[str, Any]:
        if not correlation_id:
            raise ValueError("correlation_id is required")
        try:
            sequence, previous = self.store.next_position(tenant_id)
        except Exception as exc:
            if critical:
                raise AuditUnavailableError("critical mutation blocked: audit sequencer unavailable") from exc
            raise
        safe_content, safe_metadata = redact(content), redact(metadata)
        now = values.pop("recorded_at", utc_now())
        event_id = values.pop("event_id", str(uuid.uuid4()))
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION, "event_id": event_id,
            "idempotency_key": values.pop(
                "idempotency_key", hash_json([tenant_id, event_type, action, correlation_id, resource_id])
            ),
            "tenant_id": tenant_id, "sequence": sequence, "event_type": event_type, "action": action,
            "occurred_at": values.pop("occurred_at", now), "recorded_at": now,
            "actor_type": values.pop("actor_type", "user"),
            "actor_id_pseudonymous": self.pseudonymize(actor_id, tenant_id),
            "actor_role": values.pop("actor_role", "unknown"),
            "source_system": values.pop("source_system", self.service),
            "resource_type": values.pop("resource_type", event_type.split(".")[0]),
            "resource_id_pseudonymous": self.pseudonymize(resource_id, tenant_id),
            "resource_version": values.pop("resource_version", "1"), "jurisdiction": values.pop("jurisdiction", "BR"),
            "legal_area_ids": values.pop("legal_area_ids", []),
            "classification": values.pop("classification", "confidential"),
            "retention_policy_id": values.pop("retention_policy_id", "audit-default-v1"),
            "lawful_basis_reference": values.pop("lawful_basis_reference", "REQUIRES_LEGAL_VALIDATION"),
            "content_hash_sha256": hash_json(safe_content), "metadata_hash_sha256": hash_json(safe_metadata),
            "previous_event_hash_sha256": previous, "correlation_id": correlation_id,
            "causation_id": values.pop("causation_id", None), "model_provider": values.pop("model_provider", None),
            "model_name": values.pop("model_name", None), "model_version": values.pop("model_version", None),
            "prompt_template_version": values.pop("prompt_template_version", None),
            "source_citation_hashes": values.pop("source_citation_hashes", []),
            "human_review_status": values.pop("human_review_status", "not_required"),
            "reviewer_pseudonymous": None,
            "result_status": values.pop("result_status", "success"), "error_code": values.pop("error_code", None),
            "created_by_service": self.service, "build_version": self.build_version,
        }
        reviewer_id = values.pop("reviewer_id", None)
        body["reviewer_pseudonymous"] = self.pseudonymize(reviewer_id, tenant_id) if reviewer_id else None
        if values:
            raise ValueError("unknown audit fields: " + ", ".join(sorted(values)))
        try:
            return self.store.append(seal_event(body))
        except Exception as exc:
            if critical:
                raise AuditUnavailableError("critical mutation blocked: audit evidence unavailable") from exc
            raise

    def recordMutation(self, **values: Any) -> dict[str, Any]:
        values["critical"] = True
        return self.record(**values)

    def recordAIExecution(self, **values: Any) -> dict[str, Any]:
        values.setdefault("event_type", "ai.execution")
        return self.record(**values)

    def recordSourceSnapshot(self, **values: Any) -> dict[str, Any]:
        values.setdefault("event_type", "source.snapshot")
        return self.record(**values)

    def recordHumanReview(self, **values: Any) -> dict[str, Any]:
        values.setdefault("event_type", "human.review")
        return self.record(**values)

    def verifyEvent(self, event: dict[str, Any]) -> bool:
        return verify_event(event)

    def verifyResourceHistory(self, tenant_id: str, resource_id: str) -> bool:
        from .schema import verify_chain
        all_events = self.store.events(tenant_id)
        if not verify_chain(all_events):
            return False
        pseudonym = self.pseudonymize(resource_id, tenant_id)
        return bool([event for event in all_events if event["resource_id_pseudonymous"] == pseudonym])

    def verifyBatch(self, event_hash: str, proof: Any) -> bool:
        from .merkle import verify_proof
        return verify_proof(event_hash, proof)
