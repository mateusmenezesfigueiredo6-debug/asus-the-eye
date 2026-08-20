// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
/** Local design template only. No deploy configuration or remote IDs. */
export interface Env {
  AUDIT_DB: D1Database;
  AUDIT_EVIDENCE: R2Bucket;
  AUDIT_EVENTS: Queue;
  AUDIT_SEQUENCER: DurableObjectNamespace;
  BLOCKCHAIN_BROADCAST_ENABLED: "false";
}

export default {
  async queue(batch: MessageBatch<unknown>, env: Env): Promise<void> {
    for (const message of batch.messages) {
      try {
        // Adapter must validate schema, derive stable idempotency, then call a tenant-
        // scoped Durable Object. The DO transaction allocates sequence + appends ledger.
        // Batching/anchoring consumes the committed outbox; it never accepts raw R2 data.
        void env;
        throw new Error("SKIPPED_LOCAL_SCAFFOLD");
      } catch (error) {
        const retryable = error instanceof Error && error.message !== "SCHEMA_INVALID";
        if (retryable) message.retry();
        else message.ack(); // handler persists safe failure metadata before ack in staging.
      }
    }
  },
};

export class AuditSequencer {
  constructor(private state: DurableObjectState, private env: Env) {}
  async fetch(): Promise<Response> {
    return new Response("local scaffold", { status: 501 });
  }
}
