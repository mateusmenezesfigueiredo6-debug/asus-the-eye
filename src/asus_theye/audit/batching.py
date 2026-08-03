"""Build Merkle batches from remote ledger events and store them.

The tree, manifest and inclusion proofs are produced locally by the Phase 0
audit core (keccak + domain-separated Merkle). The worker re-validates the
batch against the ledger it owns before storing, so a manifest can never claim
events that are not in the chain.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Any

from asus_theye.audit.manifest import build_manifest
from asus_theye.audit.merkle import MerkleTree
from asus_theye.audit.remote_ledger import DEFAULT_TENANT, LedgerPublishError, _ledger_token

_TIMEOUT_SECONDS = 30


def _headers() -> dict[str, str]:
    headers = {
        "content-type": "application/json",
        "user-agent": "asus-theye-batcher/0.3",
    }
    token = _ledger_token()
    if token:
        headers["authorization"] = f"Bearer {token}"
    return headers


def _get(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise LedgerPublishError(f"ledger GET failed: HTTP {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise LedgerPublishError(f"ledger unreachable: {error}") from error


def fetch_events(ledger_url: str, tenant_id: str) -> list[dict[str, Any]]:
    events = _get(f"{ledger_url.rstrip('/')}/events?tenant={tenant_id}")["events"]
    for event in events:
        event["tenant_id"] = tenant_id  # the list endpoint scopes by tenant already
    return sorted(events, key=lambda item: item["sequence"])


def fetch_batches(ledger_url: str, tenant_id: str) -> list[dict[str, Any]]:
    return _get(f"{ledger_url.rstrip('/')}/batches?tenant={tenant_id}")["batches"]


def build_batch(
    events: list[dict[str, Any]],
    previous_batch_root: str | None = None,
) -> dict[str, Any]:
    """Build the Merkle tree, manifest and one inclusion proof per event."""
    if not events:
        raise ValueError("cannot batch an empty event list")
    tree = MerkleTree(events)
    manifest = build_manifest(events, previous_batch_root=previous_batch_root)
    proofs = [
        {
            "event_id": event["event_id"],
            "sequence": event["sequence"],
            "event_hash_sha256": event["event_hash_sha256"],
            "leaf_index": index,
            "proof": asdict(tree.proof(index)),
        }
        for index, event in enumerate(tree.events)
    ]
    return {"manifest": manifest, "proofs": proofs}


def publish_batch(batch: dict[str, Any], ledger_url: str) -> dict[str, Any]:
    """Store the batch on the ledger. Fails loudly if it is rejected."""
    body = {
        "manifest": batch["manifest"],
        "proofs": [
            {"event_id": p["event_id"], "leaf_index": p["leaf_index"], "proof": p["proof"]} for p in batch["proofs"]
        ],
    }
    request = urllib.request.Request(
        f"{ledger_url.rstrip('/')}/batches",
        data=json.dumps(body).encode("utf-8"),
        headers=_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise LedgerPublishError(f"batch rejected: HTTP {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise LedgerPublishError(f"ledger unreachable: {error}") from error


def batch_pending_events(
    ledger_url: str,
    tenant_id: str = DEFAULT_TENANT,
    publish: bool = False,
) -> dict[str, Any]:
    """Batch every event after the last stored batch. No-op when up to date."""
    events = fetch_events(ledger_url, tenant_id)
    existing = fetch_batches(ledger_url, tenant_id)
    last_batched = max((b["last_sequence"] for b in existing), default=0)
    previous_root = next((b["merkle_root"] for b in existing if b["last_sequence"] == last_batched), None)
    pending = [event for event in events if event["sequence"] > last_batched]
    if not pending:
        return {"status": "up_to_date", "last_batched_sequence": last_batched, "pending": 0}

    batch = build_batch(pending, previous_batch_root=previous_root)
    result = {
        "status": "built",
        "manifest": batch["manifest"],
        "proofs": batch["proofs"],
        "pending": len(pending),
    }
    if publish:
        result["receipt"] = publish_batch(batch, ledger_url)
        result["status"] = "stored"
    return result
