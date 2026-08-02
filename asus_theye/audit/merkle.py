"""Deterministic, domain-separated, order-independent-node Merkle proofs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .keccak import keccak256


def leaf_hash(event_hash_sha256: str) -> bytes:
    try:
        raw = bytes.fromhex(event_hash_sha256)
    except ValueError as exc:
        raise ValueError("event hash must be hexadecimal") from exc
    if len(raw) != 32:
        raise ValueError("event hash must be 32 bytes")
    return keccak256(b"\x00" + raw)


def node_hash(left: bytes, right: bytes) -> bytes:
    if len(left) != 32 or len(right) != 32:
        raise ValueError("nodes must be 32 bytes")
    first, second = sorted((left, right))
    return keccak256(b"\x01" + first + second)


@dataclass(frozen=True)
class MerkleProof:
    leaf: str
    siblings: tuple[str, ...]
    root: str
    proof_format_version: str = "1"


class MerkleTree:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        if not events:
            raise ValueError("cannot build an empty Merkle tree")
        ordered = sorted(events, key=lambda event: (event["tenant_id"], event["sequence"]))
        identities = [(event["tenant_id"], event["sequence"]) for event in ordered]
        hashes = [event["event_hash_sha256"] for event in ordered]
        if len(identities) != len(set(identities)) or len(hashes) != len(set(hashes)):
            raise ValueError("duplicate event in batch")
        self.events = ordered
        self.levels = [[leaf_hash(value) for value in hashes]]
        while len(self.levels[-1]) > 1:
            level = self.levels[-1]
            self.levels.append([
                node_hash(level[index], level[index + 1] if index + 1 < len(level) else level[index])
                for index in range(0, len(level), 2)
            ])

    @property
    def root(self) -> str:
        return self.levels[-1][0].hex()

    def proof(self, index: int) -> MerkleProof:
        if index < 0 or index >= len(self.events):
            raise IndexError(index)
        siblings: list[str] = []
        position = index
        for level in self.levels[:-1]:
            sibling = position ^ 1
            if sibling >= len(level):
                sibling = position
            siblings.append(level[sibling].hex())
            position //= 2
        return MerkleProof(self.levels[0][index].hex(), tuple(siblings), self.root)


def verify_proof(event_hash_sha256: str, proof: MerkleProof | dict[str, Any]) -> bool:
    if isinstance(proof, dict):
        try:
            proof = MerkleProof(**proof)
        except (TypeError, ValueError):
            return False
    value = leaf_hash(event_hash_sha256)
    if value.hex() != proof.leaf:
        return False
    try:
        for sibling in proof.siblings:
            value = node_hash(value, bytes.fromhex(sibling))
    except ValueError:
        return False
    return value.hex() == proof.root
