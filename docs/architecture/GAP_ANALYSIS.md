# Gap analysis

| Capability | Before | Bootstrap state | Remaining gate |
| --- | --- | --- | --- |
| Event contract | Benchmark-specific JSONL | Strict schema 1.0.0, PII-free fields | Domain/legal review |
| Canonical/hash | Python sorted JSON | RFC 8785/I-JSON + deterministic vectors | Independent conformance review |
| Ledger/outbox | File hash chain | Tenant chain, SQLite invariants, transactional outbox | D1/DO integration/load tests |
| Merkle | Absent | Keccak domain separation, proof/golden vectors | Independent implementation cross-check |
| Audit SDK | Absent | Single API, HMAC IDs, redaction, fail-closed critical writes | Instrument all critical mutations |
| Cloudflare | Absent | Local Queue/DO/D1/R2 template | Approved staging resources/config |
| Verifier | Boolean JSONL check | Offline receipt with five states; endpoint facade | Authenticated service and anchor RPC adapter |
| Contract | Absent | Narrow non-upgradeable OZ5 Solidity contract | Vendored dependencies, Forge tests/audit |
| Privacy/security | Absent | LGPD design, classification, retention, threat model | DPO/legal/security approval and DPIA/RIPD decision |
| CI | Absent | Local tests and disabled-external workflow | Pin actions/dependencies and enable after review |

Critical gaps are deliberate gates, not silent fallbacks: no signer custody, no remote
storage durability evidence, no staging integration, no legal-basis determination, no
smart-contract compilation/audit and no independent verification. Mainnet is prohibited
until all phases and approvals are complete.
