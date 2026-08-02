# ADR-001 — Off-chain data, on-chain commitments

Status: accepted for prototype.

Documents and personal/content data remain encrypted off-chain; metadata/indexes stay
in tenant databases; only batch/root/manifest hashes, ranges, counts and versions are
anchored. This minimizes irreversible disclosure and cost. It requires durable storage,
key lifecycle and independent proof delivery; an anchor proves commitment, not truth.
