# ADR-004 — Deterministic domain-separated Merkle tree

Status: accepted for prototype.

Sort leaves by tenant/sequence. Leaf is `keccak256(0x00 || SHA256-event-bytes)`; node is
`keccak256(0x01 || min(left,right) || max(left,right))`; an odd node pairs with itself.
Duplicates fail. Directionless proofs are compact and deterministic, while leaf order
remains committed through the manifest range/list association.
