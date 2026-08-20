// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * THE EYE public verifier.
 *
 * This Worker has no authentication or secret and never persists request
 * bodies. Its only binding is used for SELECTs over confirmed Merkle anchors.
 */

const GENESIS_HASH = "0".repeat(64);
const HEX_64 = /^[0-9a-f]{64}$/;
const CHAIN_HASH = /^(?:0x)?[0-9a-f]{64}$/;
const SCHEMA_VERSION = "1.0.0";
const MAX_DOCUMENT_BYTES = 1024 * 1024;

interface D1Result<T> {
  results: T[];
}

interface D1Statement {
  bind(...values: unknown[]): D1Statement;
  all<T>(): Promise<D1Result<T>>;
}

interface ReadOnlyDatabase {
  prepare(query: string): D1Statement;
}

export interface Env {
  ROOTS: ReadOnlyDatabase;
}

type JsonRecord = Record<string, unknown>;

export interface VerificationResult {
  valido: boolean;
  motivo: string;
  estado: "valido" | "invalido" | "incompleto" | "nao_ancorado" | "ancora_nao_confirmada";
  verificacoes: Record<string, boolean | null>;
}

interface CheckResult {
  ok: boolean;
  reason: string;
}

const REQUIRED_EVENT_FIELDS = (
  "schema_version event_id idempotency_key tenant_id sequence event_type action occurred_at " +
  "recorded_at actor_type actor_id_pseudonymous actor_role source_system resource_type " +
  "resource_id_pseudonymous resource_version jurisdiction legal_area_ids classification " +
  "retention_policy_id lawful_basis_reference content_hash_sha256 metadata_hash_sha256 " +
  "previous_event_hash_sha256 correlation_id causation_id model_provider model_name model_version " +
  "prompt_template_version source_citation_hashes human_review_status reviewer_pseudonymous " +
  "result_status error_code created_by_service build_version"
).split(" ");

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasLoneSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index++) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return true;
      index++;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      return true;
    }
  }
  return false;
}

/** RFC 8785-compatible JSON for the I-JSON values accepted by the audit schema. */
export function canonicalJson(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "boolean" || typeof value === "string") {
    if (typeof value === "string" && hasLoneSurrogate(value)) throw new Error("invalid I-JSON string");
    return JSON.stringify(value);
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value) || (Number.isInteger(value) && !Number.isSafeInteger(value))) {
      throw new Error("number outside the I-JSON domain");
    }
    return JSON.stringify(Object.is(value, -0) ? 0 : value);
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (isRecord(value)) {
    const entries = Object.keys(value)
      .sort()
      .map((key) => {
        if (hasLoneSurrogate(key)) throw new Error("invalid I-JSON key");
        return `${JSON.stringify(key)}:${canonicalJson(value[key])}`;
      });
    return `{${entries.join(",")}}`;
  }
  throw new Error("unsupported JSON value");
}

function bytesToHex(bytes: Uint8Array): string {
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function hexToBytes(value: string): Uint8Array {
  if (!HEX_64.test(value)) throw new Error("hash must be lowercase hexadecimal");
  return Uint8Array.from(value.match(/../g) ?? [], (byte) => Number.parseInt(byte, 16));
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return bytesToHex(new Uint8Array(digest));
}

const MASK_64 = (1n << 64n) - 1n;
const KECCAK_RC = [
  0x1n, 0x8082n, 0x800000000000808an, 0x8000000080008000n, 0x808bn, 0x80000001n,
  0x8000000080008081n, 0x8000000000008009n, 0x8an, 0x88n, 0x80008009n, 0x8000000an,
  0x8000808bn, 0x800000000000008bn, 0x8000000000008089n, 0x8000000000008003n,
  0x8000000000008002n, 0x8000000000000080n, 0x800an, 0x800000008000000an,
  0x8000000080008081n, 0x8000000000008080n, 0x80000001n, 0x8000000080008008n,
];
const KECCAK_ROT = [
  [0, 36, 3, 41, 18],
  [1, 44, 10, 45, 2],
  [62, 6, 43, 15, 61],
  [28, 55, 25, 21, 56],
  [27, 20, 39, 8, 14],
];

function rotateLeft(value: bigint, count: number): bigint {
  if (count === 0) return value;
  const shift = BigInt(count);
  return ((value << shift) | (value >> (64n - shift))) & MASK_64;
}

function keccakPermutation(state: bigint[]): void {
  for (const roundConstant of KECCAK_RC) {
    const columns = Array.from({ length: 5 }, (_, x) =>
      state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20],
    );
    const deltas = columns.map((_, x) => columns[(x + 4) % 5] ^ rotateLeft(columns[(x + 1) % 5], 1));
    for (let x = 0; x < 5; x++) {
      for (let y = 0; y < 5; y++) state[x + 5 * y] = (state[x + 5 * y] ^ deltas[x]) & MASK_64;
    }
    const rotated = Array<bigint>(25).fill(0n);
    for (let x = 0; x < 5; x++) {
      for (let y = 0; y < 5; y++) {
        rotated[y + 5 * ((2 * x + 3 * y) % 5)] = rotateLeft(state[x + 5 * y], KECCAK_ROT[x][y]);
      }
    }
    for (let x = 0; x < 5; x++) {
      for (let y = 0; y < 5; y++) {
        const offset = 5 * y;
        state[x + offset] =
          (rotated[x + offset] ^ ((~rotated[((x + 1) % 5) + offset]) & rotated[((x + 2) % 5) + offset])) &
          MASK_64;
      }
    }
    state[0] = (state[0] ^ roundConstant) & MASK_64;
  }
}

/** Ethereum Keccak-256, deliberately distinct from NIST SHA3-256. */
export function keccak256(data: Uint8Array): Uint8Array {
  const rate = 136;
  const paddingLength = (rate - ((data.length + 1) % rate) - 1 + rate) % rate;
  const padded = new Uint8Array(data.length + 1 + paddingLength + 1);
  padded.set(data);
  padded[data.length] = 0x01;
  padded[padded.length - 1] = 0x80;
  const state = Array<bigint>(25).fill(0n);
  for (let offset = 0; offset < padded.length; offset += rate) {
    for (let lane = 0; lane < rate / 8; lane++) {
      let word = 0n;
      for (let byte = 0; byte < 8; byte++) word |= BigInt(padded[offset + lane * 8 + byte]) << BigInt(byte * 8);
      state[lane] ^= word;
    }
    keccakPermutation(state);
  }
  const output = new Uint8Array(32);
  for (let index = 0; index < output.length; index++) {
    output[index] = Number((state[Math.floor(index / 8)] >> BigInt((index % 8) * 8)) & 0xffn);
  }
  return output;
}

function concatBytes(...parts: Uint8Array[]): Uint8Array {
  const result = new Uint8Array(parts.reduce((total, part) => total + part.length, 0));
  let offset = 0;
  for (const part of parts) {
    result.set(part, offset);
    offset += part.length;
  }
  return result;
}

function merkleLeaf(eventHash: string): Uint8Array {
  return keccak256(concatBytes(Uint8Array.of(0), hexToBytes(eventHash)));
}

function merkleNode(first: Uint8Array, second: Uint8Array): Uint8Array {
  const ordered = bytesToHex(first) <= bytesToHex(second) ? [first, second] : [second, first];
  return keccak256(concatBytes(Uint8Array.of(1), ...ordered));
}

function validateEventSchema(event: JsonRecord): CheckResult {
  const missing = REQUIRED_EVENT_FIELDS.filter((field) => !(field in event));
  if (missing.length) return { ok: false, reason: `evento sem campo obrigatório: ${missing[0]}` };
  if (event.schema_version !== SCHEMA_VERSION) return { ok: false, reason: "schema_version não suportada" };
  if (!Number.isSafeInteger(event.sequence) || Number(event.sequence) < 1) {
    return { ok: false, reason: "sequence deve ser inteiro positivo" };
  }
  if (typeof event.correlation_id !== "string" || event.correlation_id.length === 0) {
    return { ok: false, reason: "correlation_id obrigatório" };
  }
  if (!["public", "internal", "confidential", "restricted"].includes(String(event.classification))) {
    return { ok: false, reason: "classification inválida" };
  }
  for (const field of ["content_hash_sha256", "metadata_hash_sha256", "previous_event_hash_sha256"]) {
    if (typeof event[field] !== "string" || !HEX_64.test(event[field] as string)) {
      return { ok: false, reason: `${field} não é SHA-256 hexadecimal minúsculo` };
    }
  }
  for (const field of ["occurred_at", "recorded_at"]) {
    const value = event[field];
    if (
      typeof value !== "string" ||
      !/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ||
      Number.isNaN(Date.parse(value))
    ) {
      return { ok: false, reason: `${field} não é ISO 8601 com fuso horário` };
    }
  }
  if (typeof event.event_hash_sha256 !== "string" || !HEX_64.test(event.event_hash_sha256)) {
    return { ok: false, reason: "event_hash_sha256 não é SHA-256 hexadecimal minúsculo" };
  }
  return { ok: true, reason: "esquema válido" };
}

async function verifyEvent(event: unknown): Promise<CheckResult> {
  if (!isRecord(event)) return { ok: false, reason: "evento deve ser um objeto JSON" };
  const schema = validateEventSchema(event);
  if (!schema.ok) return schema;
  const body = { ...event };
  delete body.event_hash_sha256;
  let expected: string;
  try {
    expected = await sha256Hex(canonicalJson(body));
  } catch {
    return { ok: false, reason: "evento fora do domínio I-JSON canônico" };
  }
  const received = String(event.event_hash_sha256);
  if (expected !== received) {
    return { ok: false, reason: `hash do evento esperado ${expected}, recebido ${received}` };
  }
  return { ok: true, reason: "hash do evento válido" };
}

async function verifyChain(events: unknown): Promise<CheckResult> {
  if (!Array.isArray(events)) return { ok: false, reason: "events deve ser uma lista" };
  if (events.length === 0) return { ok: true, reason: "cadeia vazia válida" };
  if (!events.every(isRecord)) return { ok: false, reason: "cada evento deve ser um objeto JSON" };
  const ordered = [...events].sort((left, right) => Number(left.sequence) - Number(right.sequence));
  const tenant = ordered[0].tenant_id;
  let expectedSequence = 1;
  let expectedPreviousHash = GENESIS_HASH;
  for (const event of ordered) {
    const receivedSequence = event.sequence;
    if (receivedSequence !== expectedSequence) {
      const safeReceived = Number.isSafeInteger(receivedSequence) ? String(receivedSequence) : "inválida";
      return {
        ok: false,
        reason: `sequência quebrada: esperada ${expectedSequence}, recebida ${safeReceived}`,
      };
    }
    if (event.tenant_id !== tenant) {
      return { ok: false, reason: `cadeia mistura tenants na sequência ${expectedSequence}` };
    }
    const candidatePreviousHash = event.previous_event_hash_sha256;
    const receivedPreviousHash =
      typeof candidatePreviousHash === "string" && HEX_64.test(candidatePreviousHash) ? candidatePreviousHash : "inválido";
    if (receivedPreviousHash !== expectedPreviousHash) {
      return {
        ok: false,
        reason:
          `encadeamento quebrado na sequência ${expectedSequence}: hash anterior esperado ` +
          `${expectedPreviousHash}, recebido ${receivedPreviousHash}`,
      };
    }
    const eventCheck = await verifyEvent(event);
    if (!eventCheck.ok) return { ok: false, reason: `sequência ${expectedSequence}: ${eventCheck.reason}` };
    expectedPreviousHash = String(event.event_hash_sha256);
    expectedSequence++;
  }
  return { ok: true, reason: `${ordered.length} evento(s) íntegro(s) desde a gênese` };
}

function verifyMerkleProof(document: JsonRecord): CheckResult {
  const eventHash = document.event_hash_sha256;
  const proof = document.proof;
  if (typeof eventHash !== "string" || !HEX_64.test(eventHash)) {
    return { ok: false, reason: "event_hash_sha256 não é SHA-256 hexadecimal minúsculo" };
  }
  if (!isRecord(proof) || typeof proof.leaf !== "string" || !Array.isArray(proof.siblings) || typeof proof.root !== "string") {
    return { ok: false, reason: "prova Merkle malformada" };
  }
  try {
    let value = merkleLeaf(eventHash);
    const expectedLeaf = bytesToHex(value);
    if (!HEX_64.test(proof.leaf)) return { ok: false, reason: "folha Merkle não é hash hexadecimal minúsculo" };
    if (expectedLeaf !== proof.leaf) {
      return { ok: false, reason: `folha Merkle esperada ${expectedLeaf}, recebida ${proof.leaf}` };
    }
    for (const sibling of proof.siblings) {
      if (typeof sibling !== "string") return { ok: false, reason: "irmão Merkle não é hash" };
      value = merkleNode(value, hexToBytes(sibling));
    }
    const expectedRoot = bytesToHex(value);
    if (!HEX_64.test(proof.root)) return { ok: false, reason: "raiz Merkle não é hash hexadecimal minúsculo" };
    if (expectedRoot !== proof.root) {
      return { ok: false, reason: `raiz Merkle esperada ${expectedRoot}, recebida ${proof.root}` };
    }
    return { ok: true, reason: "prova de inclusão Merkle válida" };
  } catch {
    return { ok: false, reason: "prova Merkle contém hash inválido" };
  }
}

function result(
  valido: boolean,
  motivo: string,
  estado: VerificationResult["estado"],
  verificacoes: Record<string, boolean | null>,
): VerificationResult {
  return { valido, motivo, estado, verificacoes };
}

/** Reimplementation of audit.verifier.verify_document without persistence. */
export async function verifyDocument(document: unknown): Promise<VerificationResult> {
  if (!isRecord(document)) return result(false, "documento deve ser um objeto JSON", "invalido", {});
  const kind = typeof document.kind === "string" ? document.kind : "event";
  if (kind === "event") {
    const check = await verifyEvent(document.event ?? document);
    return result(check.ok, check.reason, check.ok ? "nao_ancorado" : "invalido", { schema_hash: check.ok });
  }
  if (kind === "chain" || kind === "history") {
    const check = await verifyChain(document.events ?? []);
    if (!check.ok) return result(false, check.reason, "invalido", { event_chain: false });
    const anchor = document.anchor;
    if (anchor === undefined || anchor === null) {
      return result(true, `${check.reason}; âncora não fornecida`, "nao_ancorado", { event_chain: true });
    }
    if (!isRecord(anchor) || anchor.confirmed !== true) {
      return result(true, `${check.reason}; âncora não confirmada`, "ancora_nao_confirmada", { event_chain: true });
    }
    return result(true, check.reason, "valido", { event_chain: true });
  }
  if (kind === "proof") {
    const check = verifyMerkleProof(document);
    const manifest = document.manifest_hash_valid;
    const checks = { leaf_proof_root: check.ok, manifest_hash: typeof manifest === "boolean" ? manifest : null };
    if (!check.ok) return result(false, check.reason, "invalido", checks);
    if (manifest === false) return result(false, "hash do manifesto inválido", "invalido", checks);
    if (manifest !== true) return result(false, "verificação incompleta: hash do manifesto não informado", "incompleto", checks);
    const anchor = document.anchor;
    if (anchor === undefined || anchor === null) {
      return result(true, `${check.reason}; âncora não fornecida`, "nao_ancorado", checks);
    }
    if (!isRecord(anchor) || anchor.confirmed !== true) {
      return result(true, `${check.reason}; âncora não confirmada`, "ancora_nao_confirmada", checks);
    }
    return result(true, check.reason, "valido", checks);
  }
  return result(false, "tipo de verificação não suportado", "invalido", {});
}

const COMMON_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "content-type",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
};

function jsonResponse(status: number, body: unknown, cacheControl = "no-store"): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...COMMON_HEADERS, "content-type": "application/json; charset=utf-8", "cache-control": cacheControl },
  });
}

function htmlResponse(body: string): Response {
  return new Response(body, {
    status: 200,
    headers: {
      ...COMMON_HEADERS,
      "content-type": "text/html; charset=utf-8",
      "cache-control": "public, max-age=3600",
      "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
    },
  });
}

const HOME_PAGE = `<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>THE EYE — verificação pública</title>
  <style>body{font:18px/1.55 system-ui,sans-serif;max-width:760px;margin:4rem auto;padding:0 1.2rem;color:#17202a}code{background:#eef2f5;padding:.15rem .3rem}h1{line-height:1.15}</style>
</head>
<body>
  <h1>THE EYE — verificação pública</h1>
  <p>THE EYE é uma plataforma local, incremental e auditável para descobrir e acompanhar a fronteira tecnológica. Esta superfície permite conferir a integridade criptográfica da trilha sem autenticação.</p>
  <p><code>POST /verify</code> verifica localmente no Worker um documento JSON de evento, cadeia ou prova Merkle. O documento não é persistido e a resposta nunca repete seu conteúdo ou identificadores.</p>
  <p><code>GET /root/AAAA-MM-DD</code> devolve somente hashes de raízes Merkle confirmadas naquela data. <code>GET /health</code> informa apenas se o serviço está vivo.</p>
  <p>Uma prova de integridade demonstra que o registro não mudou; não demonstra que uma afirmação é verdadeira, lícita ou completa. Antes de enviar um documento, remova qualquer dado que não seja necessário para a verificação.</p>
</body>
</html>`;

interface RootRow {
  merkle_root: string;
  manifest_hash_sha256: string;
  tx_hash: string;
  block_hash: string | null;
}

function validDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
}

async function publishedRoots(date: string, env: Env): Promise<Response> {
  if (!validDate(date)) return jsonResponse(400, { encontrada: false, motivo: "data deve usar AAAA-MM-DD" });
  try {
    const { results } = await env.ROOTS.prepare(
      `SELECT b.merkle_root, b.manifest_hash_sha256, a.tx_hash, a.block_hash
         FROM audit_anchors AS a
         JOIN audit_batches AS b ON b.batch_id = a.batch_id
        WHERE a.status = 'confirmed' AND substr(a.anchored_at, 1, 10) = ?1
        ORDER BY b.merkle_root`,
    )
      .bind(date)
      .all<RootRow>();
    const roots = results
      .filter(
        (row) =>
          HEX_64.test(row.merkle_root) &&
          HEX_64.test(row.manifest_hash_sha256) &&
          CHAIN_HASH.test(row.tx_hash) &&
          (row.block_hash === null || CHAIN_HASH.test(row.block_hash)),
      )
      .map((row) => ({
        merkle_root: row.merkle_root,
        manifest_hash_sha256: row.manifest_hash_sha256,
        tx_hash: row.tx_hash,
        block_hash: row.block_hash,
      }));
    if (roots.length === 0) return jsonResponse(404, { encontrada: false }, "public, max-age=60");
    return jsonResponse(200, { encontrada: true, roots }, "public, max-age=300");
  } catch {
    return jsonResponse(503, { encontrada: false, motivo: "registro de raízes indisponível" });
  }
}

async function handleVerify(request: Request): Promise<Response> {
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (declaredLength > MAX_DOCUMENT_BYTES) {
    return jsonResponse(200, result(false, "documento excede 1 MiB", "invalido", {}));
  }
  let text: string;
  try {
    text = await request.text();
  } catch {
    return jsonResponse(200, result(false, "não foi possível ler o documento", "invalido", {}));
  }
  if (new TextEncoder().encode(text).byteLength > MAX_DOCUMENT_BYTES) {
    return jsonResponse(200, result(false, "documento excede 1 MiB", "invalido", {}));
  }
  let document: unknown;
  try {
    document = JSON.parse(text);
  } catch {
    return jsonResponse(200, result(false, "JSON inválido", "invalido", {}));
  }
  try {
    return jsonResponse(200, await verifyDocument(document));
  } catch {
    return jsonResponse(200, result(false, "documento inválido para verificação", "invalido", {}));
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: COMMON_HEADERS });
    if (url.pathname === "/health" && request.method === "GET") return jsonResponse(200, { status: "ok" });
    if (url.pathname === "/verify" && request.method === "POST") return handleVerify(request);
    if (url.pathname === "/" && request.method === "GET") return htmlResponse(HOME_PAGE);
    const rootMatch = /^\/root\/([^/]+)$/.exec(url.pathname);
    if (rootMatch && request.method === "GET") return publishedRoots(decodeURIComponent(rootMatch[1]), env);
    if (["/", "/health", "/verify"].includes(url.pathname) || rootMatch) {
      return jsonResponse(405, { erro: "método não permitido" });
    }
    return jsonResponse(404, { erro: "rota não encontrada" });
  },
};
