import assert from "node:assert/strict";
import test from "node:test";

import worker, { keccak256, verifyDocument } from "./worker.ts";

const EVENT = Object.freeze({
  schema_version: "1.0.0",
  event_id: "evt-fixed-1",
  idempotency_key: "fixed-idempotency-key-0001",
  tenant_id: "tenant-fixture",
  sequence: 1,
  event_type: "discovery.observed",
  action: "observe",
  occurred_at: "2026-08-08T12:00:00Z",
  recorded_at: "2026-08-08T12:00:01Z",
  actor_type: "service",
  actor_id_pseudonymous: "1".repeat(64),
  actor_role: "collector",
  source_system: "fixture",
  resource_type: "innovation",
  resource_id_pseudonymous: "2".repeat(64),
  resource_version: "1",
  jurisdiction: "global",
  legal_area_ids: [],
  classification: "public",
  retention_policy_id: "audit-default-v1",
  lawful_basis_reference: "public-source-fixture",
  content_hash_sha256: "3".repeat(64),
  metadata_hash_sha256: "4".repeat(64),
  previous_event_hash_sha256: "0".repeat(64),
  correlation_id: "fixture-correlation",
  causation_id: null,
  model_provider: null,
  model_name: null,
  model_version: null,
  prompt_template_version: null,
  source_citation_hashes: [],
  human_review_status: "not_required",
  reviewer_pseudonymous: null,
  result_status: "success",
  error_code: null,
  created_by_service: "public-verifier-test",
  build_version: "test",
  event_hash_sha256: "6ec98f4884e8b8f7a58e381e2fe7df79fe9990fc79352515f424b56942298b91",
});

test("fixed event and genesis chain verify without network", async () => {
  const eventReceipt = await verifyDocument({ kind: "event", event: EVENT });
  assert.equal(eventReceipt.valido, true);
  assert.equal(eventReceipt.estado, "nao_ancorado");

  const chainReceipt = await verifyDocument({ kind: "chain", events: [EVENT] });
  assert.equal(chainReceipt.valido, true);
  assert.match(chainReceipt.motivo, /desde a gênese/);
});

test("broken chain reports sequence and expected and received hashes", async () => {
  const broken = { ...EVENT, previous_event_hash_sha256: "f".repeat(64) };
  const receipt = await verifyDocument({ kind: "chain", events: [broken] });
  assert.equal(receipt.valido, false);
  assert.match(receipt.motivo, /sequência 1/);
  assert.match(receipt.motivo, new RegExp("0".repeat(64)));
  assert.match(receipt.motivo, new RegExp("f".repeat(64)));
});

test("Keccak and one-leaf Merkle proof match the Python semantics", async () => {
  assert.equal(
    Buffer.from(keccak256(new Uint8Array())).toString("hex"),
    "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470",
  );
  const leafInput = Buffer.concat([Buffer.from([0]), Buffer.from(EVENT.event_hash_sha256, "hex")]);
  const leaf = Buffer.from(keccak256(leafInput)).toString("hex");
  const receipt = await verifyDocument({
    kind: "proof",
    event_hash_sha256: EVENT.event_hash_sha256,
    proof: { leaf, siblings: [], root: leaf, proof_format_version: "1" },
    manifest_hash_valid: true,
  });
  assert.equal(receipt.valido, true);
});

test("multi-level Merkle proof matches the Python golden vector", async () => {
  const receipt = await verifyDocument({
    kind: "proof",
    event_hash_sha256: "277c1efc72ea1fc36d7cb158eda95dd50ff6cdc0ef9c9af6fe77c2dbab4b7fdc",
    proof: {
      leaf: "ec84cf04e785ed45654796264b4b1a308ef81c664822804c481c4e9e8a782cdb",
      siblings: [
        "2afea4b79d1dd4107d252f76e0cf4939214c70a868f1ed27dcf96071963f6c8c",
        "c8f83ff4af3055e208d57723416d5ca6fdfea0cfc8f535014a4ff19554cc2422",
      ],
      root: "d48851a5bbfe8101261ceb6399ca36f320325f2db119e89a0dfa1111752edca4",
      proof_format_version: "1",
    },
    manifest_hash_valid: true,
  });
  assert.equal(receipt.valido, true);
});

test("HTTP invalid document is a 200 response and never echoes event content", async () => {
  const response = await worker.fetch(
    new Request("https://verifier.test/verify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ kind: "chain", events: [{ ...EVENT, previous_event_hash_sha256: "a".repeat(64) }] }),
    }),
    {},
  );
  assert.equal(response.status, 200);
  const text = await response.text();
  assert.equal(JSON.parse(text).valido, false);
  assert.equal(text.includes("tenant-fixture"), false);
  assert.equal(text.includes("discovery.observed"), false);
});

test("health is anonymous and root lookup returns hashes only", async () => {
  const health = await worker.fetch(new Request("https://verifier.test/health"), {});
  assert.deepEqual(await health.json(), { status: "ok" });

  const row = {
    merkle_root: "1".repeat(64),
    manifest_hash_sha256: "2".repeat(64),
    tx_hash: "3".repeat(64),
    block_hash: "4".repeat(64),
    tenant_id: "must-not-leak",
    batch_id: "must-not-leak",
  };
  const env = {
    ROOTS: {
      prepare(query) {
        assert.match(query, /^SELECT /);
        assert.equal(/tenant_id|event_json|manifest_json/.test(query), false);
        return {
          bind(date) {
            assert.equal(date, "2026-08-08");
            return { async all() { return { results: [row] }; } };
          },
        };
      },
    },
  };
  const response = await worker.fetch(new Request("https://verifier.test/root/2026-08-08"), env);
  assert.equal(response.status, 200);
  const text = await response.text();
  assert.equal(text.includes("must-not-leak"), false);
  assert.deepEqual(Object.keys(JSON.parse(text).roots[0]).sort(), [
    "block_hash",
    "manifest_hash_sha256",
    "merkle_root",
    "tx_hash",
  ]);
});
