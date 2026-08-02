# ADR-008 — Transactional outbox and at-least-once delivery

Status: accepted for prototype.

The event and outbox row commit atomically. Consumers use stable idempotency and unique
tenant constraints, bounded retry and DLQ. Acknowledgement follows durable processing.
Replay keeps IDs and is reconciled; exactly-once delivery is neither promised nor needed.
