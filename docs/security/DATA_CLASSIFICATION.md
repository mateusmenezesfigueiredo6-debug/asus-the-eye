# Data classification

| Class | Examples | Audit handling | Chain |
| --- | --- | --- | --- |
| Public | Published non-personal policy/version | Hash + minimal metadata | Batch commitment only |
| Internal | Build/release IDs, aggregate health | Tenant scoped, access logged | Batch commitment only |
| Confidential | Pseudonyms, source/model IDs, event metadata | Encryption, RBAC, retention | Never individual fields |
| Restricted | Legal documents, personal data, prompts/responses, secrets | Encrypted content store only; hash after redaction | Prohibited |

Unknown data defaults to restricted. Credentials, cookies, tokens, private keys and
chain-of-thought are prohibited even off-chain in the audit event. Class downgrades need
data-owner and privacy/security approval; generated exports inherit the highest source
classification.
