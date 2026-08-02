PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS retention_policies (
  retention_policy_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  retention_days INTEGER NOT NULL CHECK (retention_days > 0),
  legal_hold_allowed INTEGER NOT NULL DEFAULT 1 CHECK (legal_hold_allowed IN (0,1)),
  disposal_method TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO retention_policies
  (retention_policy_id,name,retention_days,disposal_method)
VALUES ('audit-default-v1','Default audit evidence - legal validation pending',1825,'crypto_shred_then_tombstone');

CREATE TABLE IF NOT EXISTS audit_events (
  event_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  sequence INTEGER NOT NULL CHECK (sequence > 0),
  idempotency_key TEXT NOT NULL,
  event_type TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id_pseudonymous TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  event_hash_sha256 TEXT NOT NULL UNIQUE CHECK(length(event_hash_sha256)=64),
  previous_event_hash_sha256 TEXT NOT NULL CHECK(length(previous_event_hash_sha256)=64),
  event_json TEXT NOT NULL CHECK(json_valid(event_json)),
  UNIQUE(tenant_id, sequence),
  UNIQUE(tenant_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_audit_events_resource
  ON audit_events(tenant_id, resource_type, resource_id_pseudonymous, sequence);
CREATE INDEX IF NOT EXISTS idx_audit_events_recorded ON audit_events(tenant_id, recorded_at);

CREATE TABLE IF NOT EXISTS audit_outbox (
  outbox_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE REFERENCES audit_events(event_id),
  tenant_id TEXT NOT NULL,
  payload TEXT NOT NULL CHECK(json_valid(payload)),
  status TEXT NOT NULL CHECK(status IN ('pending','processing','published','failed','dead_letter')),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts >= 0),
  available_at TEXT NOT NULL,
  locked_until TEXT,
  last_error_code TEXT,
  published_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbox_dispatch ON audit_outbox(status, available_at);

CREATE TABLE IF NOT EXISTS audit_batches (
  batch_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  first_sequence INTEGER NOT NULL,
  last_sequence INTEGER NOT NULL,
  event_count INTEGER NOT NULL CHECK(event_count > 0),
  merkle_root TEXT NOT NULL UNIQUE CHECK(length(merkle_root)=64),
  previous_batch_root TEXT,
  manifest_hash_sha256 TEXT NOT NULL UNIQUE CHECK(length(manifest_hash_sha256)=64),
  manifest_json TEXT NOT NULL CHECK(json_valid(manifest_json)),
  status TEXT NOT NULL CHECK(status IN ('built','stored','anchor_pending','anchored','failed')),
  created_at TEXT NOT NULL,
  UNIQUE(tenant_id, first_sequence, last_sequence),
  CHECK(last_sequence >= first_sequence)
);

CREATE TABLE IF NOT EXISTS audit_batch_events (
  batch_id TEXT NOT NULL REFERENCES audit_batches(batch_id),
  event_id TEXT NOT NULL UNIQUE REFERENCES audit_events(event_id),
  leaf_index INTEGER NOT NULL CHECK(leaf_index >= 0),
  proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),
  PRIMARY KEY(batch_id,event_id), UNIQUE(batch_id,leaf_index)
);

CREATE TABLE IF NOT EXISTS audit_anchors (
  anchor_id TEXT PRIMARY KEY,
  batch_id TEXT NOT NULL UNIQUE REFERENCES audit_batches(batch_id),
  chain_id INTEGER NOT NULL,
  contract_address TEXT NOT NULL,
  tx_hash TEXT NOT NULL UNIQUE,
  block_number INTEGER,
  block_hash TEXT,
  confirmations INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK(status IN ('submitted','confirmed','reorged','failed')),
  anchored_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_verification_runs (
  verification_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('valid','invalid','incomplete','not_anchored','anchor_unconfirmed')),
  report_json TEXT NOT NULL CHECK(json_valid(report_json)),
  verified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_versions (
  tenant_id TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id_pseudonymous TEXT NOT NULL,
  version TEXT NOT NULL,
  event_id TEXT NOT NULL UNIQUE REFERENCES audit_events(event_id),
  content_hash_sha256 TEXT NOT NULL,
  is_tombstone INTEGER NOT NULL DEFAULT 0 CHECK(is_tombstone IN (0,1)),
  PRIMARY KEY(tenant_id,resource_type,resource_id_pseudonymous,version)
);

CREATE TABLE IF NOT EXISTS audit_failures (
  failure_id TEXT PRIMARY KEY,
  tenant_id TEXT,
  stage TEXT NOT NULL,
  error_code TEXT NOT NULL,
  safe_detail TEXT,
  attempts INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK(status IN ('open','retrying','resolved','dead_letter')),
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_failures_status ON audit_failures(status,last_seen_at);

-- Evidence is append-only. Corrections, deletion requests and tombstones are new events.
CREATE TRIGGER IF NOT EXISTS audit_events_no_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_events_no_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_batch_events_no_update BEFORE UPDATE ON audit_batch_events
BEGIN SELECT RAISE(ABORT, 'audit_batch_events is immutable'); END;
CREATE TRIGGER IF NOT EXISTS audit_batch_events_no_delete BEFORE DELETE ON audit_batch_events
BEGIN SELECT RAISE(ABORT, 'audit_batch_events is immutable'); END;
