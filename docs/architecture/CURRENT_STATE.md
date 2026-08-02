# Current state

Assessment date: 2026-08-02. The repository was a Python 3.10+ package (`0.2.0`) for
local classical/QUBO/QAOA benchmarking, with no runtime dependencies, optional
FastAPI/psutil, pytest tests and a minimal SHA-256-chained JSONL benchmark ledger.
There was no JavaScript workspace, cloud configuration, database migration, event
schema, Merkle proof, blockchain contract, CI or deployment automation.

The existing `AuditLedger` API and benchmark paths remain intact. The bootstrap adds a
stdlib-only high-assurance audit core alongside them: canonical JSON, versioned event,
hash chain, Keccak Merkle tree, SDK, SQLite/D1-oriented migration, offline verifier and
scaffolding boundaries. Requested `apps/`, `packages/`, `contracts/` and `infra/`
directories point to one canonical Python implementation instead of creating a second
package manager or redundant monorepo.

Local trust boundary: process + SQLite file + separately protected pseudonymization
key. Cloud and chain adapters are disabled templates. No production identity,
credential, RPC, Cloudflare identifier or signer is present.
