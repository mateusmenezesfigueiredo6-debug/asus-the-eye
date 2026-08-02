/**
 * ASUS THE EYE — staging audit worker (phase 2, partial).
 *
 * HTTP ingest -> tenant-scoped Durable Object -> append-only D1 ledger.
 * The DO serializes writes per tenant, allocating the sequence and extending
 * the SHA-256 hash chain atomically (D1 batch). Evidence blobs go to R2 keyed
 * by their own SHA-256. Corrections are new events; the D1 triggers reject any
 * UPDATE/DELETE on audit_events. Blockchain broadcasting stays disabled.
 */

export interface Env {
  AUDIT_DB: D1Database;
  AUDIT_EVIDENCE: R2Bucket;
  AUDIT_SEQUENCER: DurableObjectNamespace;
  ENVIRONMENT: string;
  BLOCKCHAIN_BROADCAST_ENABLED: string;
  AUDIT_SCHEMA_VERSION: string;
  /** Wrangler secret. All endpoints except /health require it as a Bearer token. */
  AUDIT_INGEST_TOKEN: string;
}

/** Constant-time-ish bearer check; never log or echo the token. */
function authorized(request: Request, env: Env): boolean {
  const header = request.headers.get("authorization") ?? "";
  if (!header.startsWith("Bearer ") || !env.AUDIT_INGEST_TOKEN) return false;
  const provided = header.slice(7);
  const expected = env.AUDIT_INGEST_TOKEN;
  if (provided.length !== expected.length) return false;
  let mismatch = 0;
  for (let i = 0; i < expected.length; i++) {
    mismatch |= provided.charCodeAt(i) ^ expected.charCodeAt(i);
  }
  return mismatch === 0;
}

const GENESIS_HASH = "0".repeat(64);

interface IngestBody {
  tenant_id: string;
  idempotency_key: string;
  event_type: string;
  resource_type: string;
  resource_id_pseudonymous: string;
  payload: Record<string, unknown>;
}

const REQUIRED_FIELDS: (keyof IngestBody)[] = [
  "tenant_id",
  "idempotency_key",
  "event_type",
  "resource_type",
  "resource_id_pseudonymous",
  "payload",
];

function validate(body: unknown): { ok: true; value: IngestBody } | { ok: false; error: string } {
  if (typeof body !== "object" || body === null) return { ok: false, error: "body must be a JSON object" };
  const record = body as Record<string, unknown>;
  for (const field of REQUIRED_FIELDS) {
    if (!(field in record)) return { ok: false, error: `missing field: ${field}` };
  }
  for (const field of REQUIRED_FIELDS.slice(0, 5)) {
    const value = record[field];
    if (typeof value !== "string" || value.length === 0 || value.length > 256) {
      return { ok: false, error: `${field} must be a non-empty string (max 256 chars)` };
    }
  }
  if (typeof record.payload !== "object" || record.payload === null) {
    return { ok: false, error: "payload must be a JSON object" };
  }
  return { ok: true, value: record as unknown as IngestBody };
}

/** Deterministic JSON: object keys sorted recursively, arrays preserved. */
export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (typeof value === "object" && value !== null) {
    const entries = Object.keys(value as Record<string, unknown>)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${canonicalJson((value as Record<string, unknown>)[k])}`);
    return `{${entries.join(",")}}`;
  }
  return JSON.stringify(value);
}

async function sha256Hex(data: string | ArrayBuffer): Promise<string> {
  const bytes = typeof data === "string" ? new TextEncoder().encode(data) : data;
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Fully closed surface: every endpoint, /health included, requires the token.
    if (!authorized(request, env)) {
      return json(401, { error: "unauthorized" });
    }

    if (url.pathname === "/health") {
      return json(200, {
        service: "the-eye-audit-staging",
        environment: env.ENVIRONMENT,
        schema_version: env.AUDIT_SCHEMA_VERSION,
        blockchain_broadcast_enabled: env.BLOCKCHAIN_BROADCAST_ENABLED === "true",
      });
    }

    if (url.pathname === "/events" && request.method === "POST") {
      let parsed: unknown;
      try {
        parsed = await request.json();
      } catch {
        return json(400, { error: "invalid JSON" });
      }
      const result = validate(parsed);
      if (!result.ok) return json(422, { error: result.error });

      // One DO per tenant: single-threaded execution serializes the sequence.
      const id = env.AUDIT_SEQUENCER.idFromName(result.value.tenant_id);
      const stub = env.AUDIT_SEQUENCER.get(id);
      return stub.fetch("https://sequencer/append", {
        method: "POST",
        body: JSON.stringify(result.value),
        headers: { "content-type": "application/json" },
      });
    }

    if (url.pathname === "/events" && request.method === "GET") {
      const tenant = url.searchParams.get("tenant");
      if (!tenant) return json(400, { error: "tenant query param required" });
      const { results } = await env.AUDIT_DB.prepare(
        `SELECT event_id, sequence, event_type, resource_type, recorded_at,
                event_hash_sha256, previous_event_hash_sha256
           FROM audit_events WHERE tenant_id = ?1
           ORDER BY sequence DESC LIMIT 50`,
      )
        .bind(tenant)
        .all();
      return json(200, { tenant_id: tenant, events: results });
    }

    if (url.pathname === "/evidence" && request.method === "POST") {
      const body = await request.arrayBuffer();
      if (body.byteLength === 0) return json(400, { error: "empty body" });
      if (body.byteLength > 1024 * 1024) return json(413, { error: "evidence larger than 1 MiB" });
      const hash = await sha256Hex(body);
      const key = `evidence/sha256/${hash}`;
      const existing = await env.AUDIT_EVIDENCE.head(key);
      if (existing === null) await env.AUDIT_EVIDENCE.put(key, body);
      return json(existing === null ? 201 : 200, { key, sha256: hash, deduplicated: existing !== null });
    }

    return json(404, { error: "not found" });
  },
};

export class AuditSequencer {
  constructor(
    private state: DurableObjectState,
    private env: Env,
  ) {}

  async fetch(request: Request): Promise<Response> {
    const body = (await request.json()) as IngestBody;
    const db = this.env.AUDIT_DB;

    // Idempotency: same tenant + key returns the original event, no new write.
    const duplicate = await db
      .prepare(`SELECT event_id, sequence, event_hash_sha256 FROM audit_events
                 WHERE tenant_id = ?1 AND idempotency_key = ?2`)
      .bind(body.tenant_id, body.idempotency_key)
      .first();
    if (duplicate) return json(200, { deduplicated: true, ...duplicate });

    const head = await db
      .prepare(`SELECT sequence, event_hash_sha256 FROM audit_events
                 WHERE tenant_id = ?1 ORDER BY sequence DESC LIMIT 1`)
      .bind(body.tenant_id)
      .first<{ sequence: number; event_hash_sha256: string }>();

    const sequence = (head?.sequence ?? 0) + 1;
    const previousHash = head?.event_hash_sha256 ?? GENESIS_HASH;
    const recordedAt = new Date().toISOString();
    const eventId = crypto.randomUUID();

    const hashable = {
      event_id: eventId,
      tenant_id: body.tenant_id,
      sequence,
      idempotency_key: body.idempotency_key,
      event_type: body.event_type,
      resource_type: body.resource_type,
      resource_id_pseudonymous: body.resource_id_pseudonymous,
      recorded_at: recordedAt,
      previous_event_hash_sha256: previousHash,
      payload: body.payload,
      schema_version: this.env.AUDIT_SCHEMA_VERSION,
    };
    const eventJson = canonicalJson(hashable);
    const eventHash = await sha256Hex(eventJson);

    // Atomic append: ledger row + outbox row commit together or not at all.
    // The critical-mutation rule holds: if either insert fails, both roll back.
    await db.batch([
      db
        .prepare(`INSERT INTO audit_events
            (event_id, tenant_id, sequence, idempotency_key, event_type, resource_type,
             resource_id_pseudonymous, recorded_at, event_hash_sha256,
             previous_event_hash_sha256, event_json)
           VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)`)
        .bind(
          eventId,
          body.tenant_id,
          sequence,
          body.idempotency_key,
          body.event_type,
          body.resource_type,
          body.resource_id_pseudonymous,
          recordedAt,
          eventHash,
          previousHash,
          eventJson,
        ),
      db
        .prepare(`INSERT INTO audit_outbox
            (outbox_id, event_id, tenant_id, payload, status, attempts, available_at)
           VALUES (?1,?2,?3,?4,'pending',0,?5)`)
        .bind(crypto.randomUUID(), eventId, body.tenant_id, eventJson, recordedAt),
    ]);

    return json(201, {
      event_id: eventId,
      tenant_id: body.tenant_id,
      sequence,
      event_hash_sha256: eventHash,
      previous_event_hash_sha256: previousHash,
      recorded_at: recordedAt,
    });
  }
}
