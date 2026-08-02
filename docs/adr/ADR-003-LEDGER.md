# ADR-003 — Tenant-scoped append-only hash ledger

Status: accepted for prototype.

A monotonic sequence and previous hash protect ordering per tenant. Database uniqueness
and immutable triggers reject duplicate positions and mutation. Corrections, tombstones
and retention outcomes append new events. Availability requires a tenant sequencer and
restore/reconciliation drills; timestamps are evidence, not sequence authority.
