"""Verifier app: offline receipts plus remote hash-chain verification.

Endpoints (FastAPI, created by :func:`create_verifier_app`):

- ``POST /verify`` — verify an offline audit JSON document (chain, history or
  Merkle proof) via :func:`asus_theye.audit.verifier.verify_document`.
- ``GET /remote-chain`` — fetch the tenant's events from the restricted staging
  ledger (token from env/key file, never hardcoded) and verify hash-chain
  linkage and sequence continuity, link by link.
- ``GET /health`` — liveness only; no tenant data.

The remote check proves *continuity* (each event references its predecessor's
hash, sequences are gapless down to genesis). Full recomputation of each event
hash requires ``event_json`` and stays an offline operation via the CLI.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any

from asus_theye.audit.remote_ledger import _ledger_token  # shared token discovery
from asus_theye.audit.verifier import verify_document

GENESIS_HASH = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_remote_events(ledger_url: str, tenant_id: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        f"{ledger_url.rstrip('/')}/events?tenant={tenant_id}",
        headers={
            "user-agent": "asus-theye-verifier/0.3",
            "authorization": f"Bearer {_ledger_token() or ''}",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))["events"]


def verify_remote_chain(events: list[dict[str, Any]], tenant_id: str) -> dict[str, Any]:
    """Verify linkage/continuity of ledger events (any order in, verified asc)."""
    ordered = sorted(events, key=lambda e: e["sequence"])
    checks = {
        "has_events": bool(ordered),
        "sequence_contiguous": True,
        "hash_linkage": True,
        "genesis_ok": True,
    }
    problems: list[str] = []
    previous_hash = GENESIS_HASH
    expected_sequence = ordered[0]["sequence"] if ordered else 1
    if ordered and ordered[0]["sequence"] == 1 and ordered[0]["previous_event_hash_sha256"] != GENESIS_HASH:
        checks["genesis_ok"] = False
        problems.append("first event does not chain from genesis")
    first_sequence = ordered[0]["sequence"] if ordered else 1
    for event in ordered:
        if event["sequence"] != expected_sequence:
            checks["sequence_contiguous"] = False
            problems.append(f"gap: expected sequence {expected_sequence}, got {event['sequence']}")
            expected_sequence = event["sequence"]
        if event["sequence"] > first_sequence and event["previous_event_hash_sha256"] != previous_hash:
            checks["hash_linkage"] = False
            problems.append(f"sequence {event['sequence']} does not reference predecessor hash")
        previous_hash = event["event_hash_sha256"]
        expected_sequence += 1
    status = "valid_linkage" if all(checks.values()) else "invalid"
    return {
        "receipt_version": "1",
        "target_type": "remote_chain",
        "target_id": tenant_id,
        "status": status,
        "events_verified": len(ordered),
        "head_sequence": ordered[-1]["sequence"] if ordered else 0,
        "head_hash": ordered[-1]["event_hash_sha256"] if ordered else None,
        "checks": checks,
        "problems": problems,
        "verified_at": _now(),
        "note": "linkage/continuity proof; full hash recomputation is offline via `asus-theye audit-verify`",
    }


def create_verifier_app() -> Any:
    try:
        from fastapi import FastAPI, HTTPException, Query
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra (fastapi) to run the verifier app") from exc

    app = FastAPI(title="ASUS THE EYE Verifier", version="0.3.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "local", "broadcast": "disabled"}

    @app.post("/verify")
    def post_verify(body: dict[str, Any]) -> Any:
        receipt = verify_document(body)
        if receipt["status"] == "invalid":
            raise HTTPException(status_code=422, detail=receipt)
        return receipt

    @app.get("/remote-chain")
    def remote_chain(tenant: str = Query(...)) -> Any:
        ledger_url = os.environ.get("THE_EYE_LEDGER_URL", "")
        if not ledger_url:
            raise HTTPException(status_code=503, detail="THE_EYE_LEDGER_URL not configured")
        events = fetch_remote_events(ledger_url, tenant)
        receipt = verify_remote_chain(events, tenant)
        if receipt["status"] != "valid_linkage":
            raise HTTPException(status_code=422, detail=receipt)
        return receipt

    return app
