# Audit worker

Reference consumer for R2 notifications/Queue. The deployed design validates schema,
authenticity and tenant, deduplicates by `(tenant_id,idempotency_key)`, asks a Durable
Object SQLite sequencer for the next position, appends to the ledger and batches only
committed events. A message is acknowledged only after durable completion. Transient
errors retry with bounded exponential backoff; poison messages enter
`the-eye-audit-dlq`. Replay preserves the original idempotency key.

This directory is local scaffolding only. See `infra/cloudflare/` for disabled templates.
