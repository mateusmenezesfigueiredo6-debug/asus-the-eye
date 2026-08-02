# Cloudflare local templates

Intended flow:

`R2 notification → the-eye-audit-events → schema/idempotency → tenant Durable Object
SQLite sequencer → append-only ledger/outbox → batcher → storage adapter → anchor adapter`.

Delivery is at-least-once. Stable idempotency keys and unique tenant constraints make
replay safe. Retry uses capped exponential backoff with jitter; exhausted/poison events
are recorded in `audit_failures` and moved to `the-eye-audit-dlq`. DLQ replay requires
incident/change approval, preserves IDs, supports dry-run, and compares counts/hashes.

Alarms drive stale-lock recovery and max-age batching. Metrics: received, accepted,
duplicate, invalid, retry, DLQ depth/age, sequence conflicts, outbox lag, batch age,
anchor lag/confirmations/reorg and verification failures. Alerts must page on sustained
DLQ growth, chain gaps, bypass attempts, anchor lag and signer/RPC anomalies.

Bindings are placeholders. No R2 notification, Queue, D1, R2, Durable Object or Worker
resource was created or changed.
