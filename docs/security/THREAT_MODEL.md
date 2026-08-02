# Threat model

Risk is residual after listed controls; staging requires named owners and tests.

| Asset / agent | Vector | Impact | Prevention | Detection / response | Residual |
| --- | --- | --- | --- | --- | --- |
| Event / insider | Byte tamper | False history | Canonical hash, immutable rows | Verify chain; isolate/restore | Low |
| Ordering / producer | Reorder or delete | Misleading timeline | Tenant sequencer, previous hash | Gap/range reconciliation; stop tenant | Medium |
| Outbox / retry | Duplicate/replay | Double effects/cost | Stable idempotency, unique keys | Duplicate metric; safe replay | Low |
| SDK / developer | Critical mutation bypass | Missing evidence | Single SDK, fail closed, coverage gate | Mutation tests/runtime gap alarms | Medium |
| Queue/DLQ / attacker | Poison, flood, stuck replay | Loss/delay/DoS | Validation, quotas, bounded retry | DLQ age/rate; quarantine | Medium |
| Canonicalizer / supply chain | Divergent encoding | Root mismatch | Dependency-free pinned vectors | Cross-implementation audit; freeze batches | Medium |
| Clock / host | Skew/backdating | Incorrect narrative | Sequence authoritative, UTC validation | Drift alert; annotate recovery | Medium |
| Idempotency / caller | Collision/unstable key | Wrong dedupe | SHA-256 scoped inputs + uniqueness | Conflict alert/manual reconcile | Low |
| Tenant/admin | Missing auth/cross-tenant query | Disclosure/corruption | Tenant-scoped DO/RBAC, no RLS assumption | Canary/access audit; contain credentials | High until integration |
| PII / developer | Raw content/prompt in metadata | Privacy breach | Closed schema, redaction, classification | DLP/schema gate; incident/DPO review | Medium |
| Correlation / observer | Hash/dictionary/timing linkage | Re-identification | HMAC pseudonyms; batch aggregation | Privacy review/rotate key | Medium |
| Signer / attacker | Key theft/role abuse | Fraudulent anchors | KMS/HSM, limits, role separation, pause | Independent chain alerts; revoke/pause | High until implemented |
| RPC / provider | Wrong chain/censorship | False status or delay | Chain allowlist, quorum, confirmations | Compare RPC/block hashes; fail incomplete | Medium |
| Chain / validators | Reorg | Anchor reversal | Confirmation policy/idempotent resubmit | Reorg monitor; mark reorged | Medium |
| Contract/admin | Duplicate/root substitution | Ambiguous evidence | Immutable mappings/custom errors | Event/state reconciliation; pause | Low |
| Retention/operator | Premature/failed deletion | Violation or loss | Holds, approvals, crypto-shred workflow | Deletion receipt/restore drill | Medium |
| Gas/market | Cost spike/front-running | Delayed anchor/cost | Batch/fee/circuit limits | Cost/lag alert; keep off-chain evidence | Medium |
| Cloud/RPC outage | Ingestion/anchor unavailable | Audit gap/delay | Transactional outbox, retry, multi-provider plan | SLO alert; expose not_anchored | Medium |
| Batcher/operator | Delayed anchor | Longer tamper window | Max age/size alarms | Anchor lag page/manual recovery | Medium |
| Proof/storage corruption | Bad or unavailable proof | Cannot verify | Checksums, redundant encrypted storage | Scheduled sampling/restore | Medium |
| Dependency/build attacker | Malicious package/action | Key/data compromise | Minimal deps, review, CodeQL/SBOM/pinning | Provenance/scan; revoke/rebuild | Medium |
| AI/operator | CoT or sensitive tool output logged | Confidentiality breach | Hash/redact, explicit prohibition | Schema/DLP review; purge off-chain keys | Medium |

Trust-boundary diagram: `docs/architecture/THREAT_BOUNDARIES.mmd`. Assumptions include
honest approved administrators, correct tenant auth integration, protected platform
keys and a reviewed cryptographic implementation; these are validation targets, not
facts established by the local prototype.
