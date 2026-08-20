# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Versioned, PII-free audit-event validation and hashing."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from .canonical import canonical_bytes

SCHEMA_VERSION = "1.0.0"
GENESIS_HASH = "0" * 64
HEX64 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_FIELDS = (
    "schema_version event_id idempotency_key tenant_id sequence event_type action occurred_at "
    "recorded_at actor_type actor_id_pseudonymous actor_role source_system resource_type "
    "resource_id_pseudonymous resource_version jurisdiction legal_area_ids classification "
    "retention_policy_id lawful_basis_reference content_hash_sha256 metadata_hash_sha256 "
    "previous_event_hash_sha256 correlation_id causation_id model_provider model_name model_version "
    "prompt_template_version source_citation_hashes human_review_status reviewer_pseudonymous "
    "result_status error_code created_by_service build_version"
).split()


class EventValidationError(ValueError):
    pass


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def hash_json(value: Any) -> str:
    return sha256_hex(canonical_bytes(value))


def validate_event(event: dict[str, Any], *, require_hash: bool = True) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in event]
    if missing:
        raise EventValidationError("missing fields: " + ", ".join(missing))
    if event["schema_version"] != SCHEMA_VERSION:
        raise EventValidationError("unsupported schema_version")
    if not isinstance(event["sequence"], int) or event["sequence"] < 1:
        raise EventValidationError("sequence must be a positive integer")
    if not event["correlation_id"]:
        raise EventValidationError("correlation_id is required")
    if event["classification"] not in {"public", "internal", "confidential", "restricted"}:
        raise EventValidationError("invalid classification")
    for field in ("content_hash_sha256", "metadata_hash_sha256", "previous_event_hash_sha256"):
        if not HEX64.fullmatch(event[field]):
            raise EventValidationError(f"{field} must be lowercase SHA-256")
    for field in ("occurred_at", "recorded_at"):
        try:
            parsed = datetime.fromisoformat(event[field].replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise EventValidationError(f"{field} must be ISO 8601") from exc
        if parsed.tzinfo is None:
            raise EventValidationError(f"{field} must include timezone")
    if require_hash and not HEX64.fullmatch(event.get("event_hash_sha256", "")):
        raise EventValidationError("event_hash_sha256 must be lowercase SHA-256")


def event_hash(event: dict[str, Any]) -> str:
    body = {key: value for key, value in event.items() if key != "event_hash_sha256"}
    validate_event(body, require_hash=False)
    return hash_json(body)


def seal_event(event: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(event)
    sealed["event_hash_sha256"] = event_hash(sealed)
    return sealed


def verify_event(event: dict[str, Any]) -> bool:
    try:
        validate_event(event)
        return event["event_hash_sha256"] == event_hash(event)
    except (EventValidationError, TypeError):
        return False


def verify_chain(events: list[dict[str, Any]], *, genesis_hash: str = GENESIS_HASH) -> bool:
    if not events:
        return True
    ordered = sorted(events, key=lambda item: item["sequence"])
    tenant = ordered[0]["tenant_id"]
    previous = genesis_hash
    expected_sequence = ordered[0]["sequence"]
    for event in ordered:
        if (
            event["tenant_id"] != tenant
            or event["sequence"] != expected_sequence
            or event["previous_event_hash_sha256"] != previous
            or not verify_event(event)
        ):
            return False
        previous = event["event_hash_sha256"]
        expected_sequence += 1
    return True
