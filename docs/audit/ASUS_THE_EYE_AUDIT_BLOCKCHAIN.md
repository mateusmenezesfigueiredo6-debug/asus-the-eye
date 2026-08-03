# ASUS + THE EYE audit and blockchain architecture

The authoritative documents remain off-chain, encrypted with per-object envelope keys.
Searchable non-content metadata lives in tenant-scoped databases/indexes. Every critical
mutation produces a canonical, PII-free audit event and transactional outbox entry. A
tenant sequencer assigns a monotonic sequence and previous-event hash. The batcher
orders by tenant/sequence, creates domain-separated Keccak Merkle proofs, persists an
SHA-256-hashed manifest and hands only `(batchId, merkleRoot, manifestHash, ranges,
counts, versions)` to a gated anchor adapter.

On-chain state is evidence of existence/integrity, not truth, authorization or document
storage. No PII, document, prompt/response, source body, secret, storage URL containing
identity or chain-of-thought crosses the contract ABI. Verification independently
checks event hash, tenant/resource history, proof/root, manifest and—when configured—
confirmed anchor/reorg status.

Security properties: append-only correction, tombstones, HMAC pseudonyms scoped by
tenant, least-privilege roles, fail-closed critical mutations, outbox atomicity,
at-least-once idempotency, duplicate batch/root rejection, delayed admin transfer and
manual promotion gates. Availability and correctness are monitored independently;
delayed anchoring never makes an event silently “valid”.

See `docs/architecture/`, `docs/security/`, ADRs, diagrams and the bootstrap report.
