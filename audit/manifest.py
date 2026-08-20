# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Merkle batch manifest generation."""

from __future__ import annotations

import uuid
from typing import Any

from .merkle import MerkleTree
from .schema import SCHEMA_VERSION, hash_json
from .sdk import utc_now


def build_manifest(
    events: list[dict[str, Any]],
    *,
    previous_batch_root: str | None = None,
    storage_reference: str | None = None,
    generator_version: str = "0.3.0",
) -> dict[str, Any]:
    tenants = {event["tenant_id"] for event in events}
    if len(tenants) != 1:
        raise ValueError("a batch must contain exactly one tenant")
    tree = MerkleTree(events)
    ordered = tree.events
    manifest: dict[str, Any] = {
        "batch_id": str(uuid.uuid4()),
        "tenant_id": ordered[0]["tenant_id"],
        "schema_version": SCHEMA_VERSION,
        "first_sequence": ordered[0]["sequence"],
        "last_sequence": ordered[-1]["sequence"],
        "event_count": len(ordered),
        "merkle_root": tree.root,
        "previous_batch_root": previous_batch_root,
        "generated_at": utc_now(),
        "generator_version": generator_version,
        "proof_format_version": "1",
        "storage_reference": storage_reference,
        "blockchain_chain_id": None,
        "blockchain_tx_hash": None,
        "blockchain_block_number": None,
        "blockchain_confirmations": None,
    }
    manifest["manifest_hash_sha256"] = hash_json(manifest)
    return manifest
