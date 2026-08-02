# Incident response

Severity 1 includes suspected ledger/root tampering, cross-tenant disclosure, signer
compromise, unauthorized anchor/admin action, unrecoverable sequence loss or PII on
chain. Severity 2 includes sustained DLQ/anchor lag, verifier disagreement, reorg beyond
policy or audit bypass without known disclosure.

## Lifecycle

Detect and page from independent metrics; open an incident ID; preserve clocks, logs,
build/SBOM, manifests, proofs, receipts and chain observations as read-only evidence.
Contain by disabling the affected producer/tenant adapter, leaving broadcast false and,
when authorized, pausing the contract/revoking operational roles. Do not destroy keys or
data during triage. Assess LGPD notification duties with DPO/legal—technical staff do
not decide reportability alone. Eradicate, restore from verified state, replay
idempotently, re-verify end-to-end and obtain business/security approval before resume.

The incident event contains pseudonymous IDs, timestamps, classifications and hashes,
not narrative evidence or personal data. Detailed evidence stays encrypted off-chain
with case-scoped access. Post-incident work records root cause, detection gap, tenant
impact, regulatory decisions, owner and deadline. If PII is ever anchored, immutability
prevents deletion: immediately contain, seek legal counsel and document chain-specific
mitigation; never attempt a covert replacement.
