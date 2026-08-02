# Deployment gates

All boxes must be checked and evidenced for the target environment.

- [ ] Architecture, threat model and data-flow review approved.
- [ ] DPO/legal validates purpose, lawful basis, retention and RIPD/DPIA need.
- [ ] Every critical mutation uses the SDK and fails closed; bypass test passes.
- [ ] Tenant authorization/isolation, backup/restore, DLQ replay and crypto-shredding tested.
- [ ] Schema/canonical/Merkle cross-implementation vectors independently verified.
- [ ] Contract dependencies vendored/reviewed; tests, static analysis and independent audit pass.
- [ ] Signer uses approved KMS/HSM/service, separation of duties, limits and rotation drill.
- [ ] RPC quorum/reorg/confirmation policy and outage mode tested.
- [ ] Cost/gas/storage/Queue limits, SLOs, alerts and manual rollback accepted.
- [ ] `BLOCKCHAIN_BROADCAST_ENABLED` is false in source/default and true only in an
      approved, time-bounded execution context.
- [ ] Staging change ticket identifies chain ID and contract bytecode/address.
- [ ] Production/mainnet has a separate governance decision; no staging approval carries over.

Immediate stop conditions: PII/content in event or calldata; chain mismatch; unapproved
signer; root/manifest mismatch; sequence gap; unreviewed schema; disabled monitoring;
unbounded retry/gas; or inability to prove restore/reconciliation.
