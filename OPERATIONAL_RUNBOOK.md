# Operational runbook

## Normal operation

Watch received/accepted/duplicate/invalid rates, sequence conflicts, outbox and DLQ
age, batch size/age, storage failures, anchor lag/confirmations/reorgs and verifier
failures by tenant-safe aggregate. Never log event bodies or identifiers. Reconcile
`events = batched + eligible-unbatched`, batch event count/range, manifest hash, stored
object checksum and confirmed contract fields.

## Recovery

1. Freeze anchoring (broadcast remains false) if root, chain, signer or RPC is suspect.
2. Keep ingestion/ledger running when safe; expose `not_anchored`, never “valid”.
3. Quarantine malformed items with error code and safe digest; do not paste payloads.
4. Replay DLQ only under incident/change ticket, dry-run first, preserving event and
   idempotency IDs. Compare pre/post counts and hashes.
5. For a sequence gap, stop that tenant sequencer, reconcile committed SQLite/outbox,
   restore from a tested point if needed, and append a recovery event. Never renumber.
6. For reorg, mark anchor `reorged`, wait policy confirmations and resubmit the identical
   commitment under approved procedure; never replace the root for an existing batch.

## Key and retention operations

Rotate pseudonymization/encryption/signing keys independently with dual-read versions
and documented custody. A signer compromise pauses the contract and revokes role after
governance approval. Crypto-shredding removes the correct envelope key after legal-hold
checks; append a non-identifying tombstone and verification evidence.

Backups, restore drills, clock drift, Queue replay and RPC outage are exercised at least
quarterly. Production commands are intentionally absent; the safe local commands are
listed in the final report.
