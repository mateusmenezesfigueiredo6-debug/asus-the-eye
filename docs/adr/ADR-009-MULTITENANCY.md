# ADR-009 — Tenant isolation before global aggregation

Status: accepted for prototype.

Sequencing, chains, batches, pseudonyms, authorization and query keys are tenant scoped.
No cross-tenant proof/API lookup is implicit. SQLite/D1 lacks row-level security, so
application authorization and tenant Durable Objects are mandatory and tested. Global
operational metrics are bounded aggregates only.
