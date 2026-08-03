"""Tests for the verifier app's remote chain verification."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.verifier.app import GENESIS_HASH, verify_remote_chain


def make_chain(n: int) -> list[dict]:
    events, previous = [], GENESIS_HASH
    for seq in range(1, n + 1):
        current = f"{seq:064x}"
        events.append(
            {
                "sequence": seq,
                "event_hash_sha256": current,
                "previous_event_hash_sha256": previous,
            }
        )
        previous = current
    return events


def test_valid_chain_passes() -> None:
    receipt = verify_remote_chain(make_chain(7), "tenant-demo")
    assert receipt["status"] == "valid_linkage"
    assert receipt["events_verified"] == 7
    assert receipt["head_sequence"] == 7
    assert receipt["problems"] == []


def test_broken_linkage_detected() -> None:
    chain = make_chain(5)
    chain[3]["previous_event_hash_sha256"] = "f" * 64  # tamper
    receipt = verify_remote_chain(chain, "tenant-demo")
    assert receipt["status"] == "invalid"
    assert receipt["checks"]["hash_linkage"] is False


def test_sequence_gap_detected() -> None:
    chain = [e for e in make_chain(6) if e["sequence"] != 4]
    receipt = verify_remote_chain(chain, "tenant-demo")
    assert receipt["status"] == "invalid"
    assert receipt["checks"]["sequence_contiguous"] is False


def test_bad_genesis_detected() -> None:
    chain = make_chain(3)
    chain[0]["previous_event_hash_sha256"] = "a" * 64
    receipt = verify_remote_chain(chain, "tenant-demo")
    assert receipt["status"] == "invalid"
    assert receipt["checks"]["genesis_ok"] is False


def test_empty_chain_is_invalid() -> None:
    receipt = verify_remote_chain([], "tenant-demo")
    assert receipt["status"] == "invalid"
    assert receipt["checks"]["has_events"] is False
