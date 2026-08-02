# Cloudflare staging provisioning record

Phase 2 staging resources, provisioned via Cloudflare MCP with recorded human
approval in the interactive session of 2026-08-02.

## Approval

- Requested by: Claude (session 2026-08-02, Claude Code desktop)
- Approved by: repository owner, interactively, before any external write
- Scope approved: create D1 database + apply migration 0001 + create R2 bucket
- Cost note: all resources within Cloudflare free tier at creation time

## Resources

| Resource | Name | ID / detail |
| --- | --- | --- |
| D1 database | `the-eye-audit-staging` | `6a7a2c73-653f-4a2e-9d9d-62f7d83914ea` (region ENAM, created 2026-08-02T08:28:38Z) |
| R2 bucket | `the-eye-audit-staging` | location ENAM, Standard class, created 2026-08-02T08:30:00Z |

## Migration applied

`migrations/0001_audit_ledger.sql`, with two deviations required by the D1 HTTP
query API:

1. `PRAGMA foreign_keys = ON` omitted — D1 enforces foreign keys by default and
   rejects this pragma.
2. The four `CREATE TRIGGER` statements were applied one per request because the
   D1 query API splits batched SQL on `;`, which breaks trigger `BEGIN ... END`
   bodies.

## Post-apply verification

`sqlite_master` query confirmed 9 tables, 4 indexes, 4 triggers:

- tables: audit_anchors, audit_batch_events, audit_batches, audit_events,
  audit_failures, audit_outbox, audit_verification_runs, resource_versions,
  retention_policies
- triggers: audit_events_no_update/no_delete,
  audit_batch_events_no_update/no_delete (append-only enforcement)

## Not yet provisioned (still gated)

- Queue and Durable Object bindings (roadmap phase 2 continues)
- Worker deployment (`infra/cloudflare/worker.ts`)
- Any phase 3 blockchain resource — broadcasting remains disabled
