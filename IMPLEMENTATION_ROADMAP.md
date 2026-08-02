# Implementation roadmap

No phase promotes automatically. Each exit requires recorded human approval.

| Phase | Scope | Exit criteria |
| --- | --- | --- |
| 0 — local prototype | Schema/core/SDK/SQLite/Merkle/verifier/contract source | Deterministic tests pass; gaps and risks documented |
| 1 — integration | Instrument critical domain mutations and auth/AI flows | Coverage manifest has no unjustified gaps; fail-closed and replay tests pass |
| 2 — Cloudflare staging | Approved isolated D1/R2/Queue/DO bindings | Tenant isolation, restore, DLQ, load, alarms and cost bounds validated |
| 3 — Base Sepolia 84532 | Gated signer and anchor/confirmation/reorg adapter | Contract audit tests; operational exercise; broadcast approvals per change |
| 4 — independent audit | Application, privacy, contract and operations audit | High/critical findings closed; residual risk accepted in writing |
| 5 — pilot | Limited tenants/data classes with rollback | SLOs, legal basis, DSAR/retention and incident drill accepted |
| 6 — approved chain/mainnet | Chain selected by governance; Base mainnet only if approved | Executive/DPO/legal/security/finance approvals and production readiness review |

TODOs are valid only with owner, reason, risk, precondition and objective completion
criterion, as enforced for every `planned` coverage item.
