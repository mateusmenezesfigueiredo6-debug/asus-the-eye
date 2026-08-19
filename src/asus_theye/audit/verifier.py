"""Offline verifier producing machine-readable receipts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .merkle import verify_proof
from .schema import hash_json, verify_chain, verify_event


def _infer_kind(document: dict[str, Any]) -> str:
    """Classify unwrapped CLI documents without treating unknown shapes as events."""
    candidates: list[str] = []
    if "manifest" in document and "proofs" in document:
        candidates.append("batch")
    if "events" in document:
        candidates.append("chain")
    event_markers = {"schema_version", "event_id", "sequence", "event_hash_sha256"}
    if "event" in document or event_markers.issubset(document):
        candidates.append("event")
    if "event_hash_sha256" in document and "proof" in document:
        candidates.append("proof")
    if len(candidates) > 1:
        raise ValueError("ambiguous verification document: matches " + ", ".join(candidates))
    if not candidates:
        raise ValueError("cannot infer verification kind from document shape")
    return candidates[0]


def _proof_matches_root(item: Any, merkle_root: Any) -> bool:
    if not isinstance(item, dict) or not isinstance(item.get("proof"), dict):
        return False
    if item["proof"].get("root") != merkle_root:
        return False
    try:
        return verify_proof(item["event_hash_sha256"], item["proof"])
    except (KeyError, TypeError, ValueError):
        return False


def _verify_batch(document: dict[str, Any]) -> dict[str, Any]:
    manifest = document.get("manifest")
    proofs = document.get("proofs")
    checks: dict[str, bool | None]
    if not isinstance(manifest, dict) or not isinstance(proofs, list):
        checks = {"leaf_proof_root": False, "manifest_hash": False}
        batch_id = "unknown"
    else:
        manifest_body = dict(manifest)
        claimed_hash = manifest_body.pop("manifest_hash_sha256", None)
        manifest_valid = isinstance(claimed_hash, str) and hash_json(manifest_body) == claimed_hash
        proof_count_valid = (
            bool(proofs) and isinstance(manifest.get("event_count"), int) and len(proofs) == manifest["event_count"]
        )
        proofs_valid = proof_count_valid and all(
            _proof_matches_root(item, manifest.get("merkle_root")) for item in proofs
        )
        checks = {
            "leaf_proof_root": proofs_valid,
            "manifest_hash": manifest_valid,
        }
        batch_id = manifest.get("batch_id", "unknown")
    return verification_receipt(
        target_type="batch",
        target_id=batch_id,
        checks=checks,
        anchor=document.get("anchor"),
    )


def verification_receipt(
    *, target_type: str, target_id: str, checks: dict[str, bool | None], anchor: dict[str, Any] | None = None
) -> dict[str, Any]:
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
    return {
        "receipt_version": "1",
        "target_type": target_type,
        "target_id": target_id,
        "status": status,
        "checks": checks,
        "anchor": anchor,
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def verify_document(document: dict[str, Any]) -> dict[str, Any]:
    kind = document.get("kind") or _infer_kind(document)
    if kind == "event":
        event = document.get("event", document)
        return verification_receipt(
            target_type="event", target_id=event.get("event_id", "unknown"), checks={"schema_hash": verify_event(event)}
        )
    if kind in {"chain", "history"}:
        events = document.get("events", [])
        return verification_receipt(
            target_type=kind,
            target_id=document.get("tenant_id", "unknown"),
            checks={"event_chain": verify_chain(events)},
            anchor=document.get("anchor"),
        )
    if kind == "proof":
        valid = verify_proof(document["event_hash_sha256"], document["proof"])
        checks = {"leaf_proof_root": valid, "manifest_hash": document.get("manifest_hash_valid")}
        return verification_receipt(
            target_type="proof",
            target_id=document.get("batch_id", "unknown"),
            checks=checks,
            anchor=document.get("anchor"),
        )
    if kind == "batch":
        return _verify_batch(document)
    raise ValueError(f"unsupported verification kind: {kind}")


def verify_file(input_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    receipt = verify_document(json.loads(input_path.read_text(encoding="utf-8")))
    if output_path:
        output_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt
