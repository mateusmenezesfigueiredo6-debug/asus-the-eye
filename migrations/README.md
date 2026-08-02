# Audit migrations

`0001_audit_ledger.sql` targets SQLite/D1-compatible SQL and is safe to re-run locally.
Tenant isolation must additionally be enforced by the application and authorization
layer because D1/SQLite has no native row-level security. Production migration remains
gated; no remote migration command belongs in automation.

Corrections, tombstones and retention actions append events. They never mutate
`audit_events`. Crypto-shredding destroys separately managed envelope keys while the
non-identifying integrity record remains.
