"""Offline verifier producing machine-readable receipts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .merkle import verify_proof
from .schema import verify_chain, verify_event


def verification_receipt(*, target_type: str, target_id: str, checks: dict[str, bool | None],
                         anchor: dict[str, Any] | None = None) -> dict[str, Any]:
    if any(value is False for value in checks.values()):
        status = "invalid"
    elif any(value is None for value in checks.values()):
        status = "incomplete"
    elif anchor is None:
        status = "not_anchored"
    elif not anchor.get("confirmed", False):
        status = "anchor_unconfirmed"
    else:
        status = "valid"
    return {"receipt_version":"1", "target_type":target_type, "target_id":target_id,
            "status":status, "checks":checks, "anchor":anchor,
            "verified_at":datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}


def verify_document(document: dict[str, Any]) -> dict[str, Any]:
    kind = document.get("kind", "event")
    if kind == "event":
        event = document.get("event", document)
        return verification_receipt(target_type="event", target_id=event.get("event_id", "unknown"),
                                    checks={"schema_hash": verify_event(event)})
    if kind in {"chain", "history"}:
        events = document.get("events", [])
        return verification_receipt(target_type=kind, target_id=document.get("tenant_id", "unknown"),
                                    checks={"event_chain": verify_chain(events)}, anchor=document.get("anchor"))
    if kind == "proof":
        valid = verify_proof(document["event_hash_sha256"], document["proof"])
        checks = {"leaf_proof_root": valid, "manifest_hash": document.get("manifest_hash_valid")}
        return verification_receipt(target_type="proof", target_id=document.get("batch_id", "unknown"),
                                    checks=checks, anchor=document.get("anchor"))
    raise ValueError(f"unsupported verification kind: {kind}")


def verify_file(input_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    receipt = verify_document(json.loads(input_path.read_text(encoding="utf-8")))
    if output_path:
        output_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt
