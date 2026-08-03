"""Audited wrapper around the local LLM.

Every call produces a local JSONL audit record (hash-chained, full text hashes
only) and can optionally anchor that record on the remote staging ledger. Raw
prompts and responses never leave the machine — the remote event carries
cryptographic hashes and telemetry only, per the off-chain rule (ADR-001) and
the SDK's sensitive-key policy (prompt/response/content are redacted keys).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asus_theye.audit.remote_ledger import DEFAULT_TENANT, publish_event
from asus_theye.llm.ollama_client import OllamaClient

GENESIS_HASH = "0" * 64
DEFAULT_LOG_PATH = Path("reports/llm/calls.jsonl")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class AuditedLocalLLM:
    """Local model calls with mandatory, hash-chained audit records."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        log_path: Path = DEFAULT_LOG_PATH,
        ledger_url: str | None = None,
        tenant_id: str = DEFAULT_TENANT,
    ) -> None:
        self.client = client or OllamaClient()
        self.log_path = log_path
        self.ledger_url = ledger_url
        self.tenant_id = tenant_id

    def _previous_hash(self) -> str:
        if not self.log_path.exists():
            return GENESIS_HASH
        last_line = ""
        with self.log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last_line = line
        if not last_line:
            return GENESIS_HASH
        return json.loads(last_line).get("record_hash_sha256", GENESIS_HASH)

    def chat(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> dict[str, Any]:
        """Call the local model; returns {content, audit_record, ledger_receipt}."""
        result = self.client.chat(prompt, system=system, temperature=temperature)

        record = {
            "called_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "model": result["model"],
            "backend": "ollama_local",
            "prompt_sha256": _sha256(prompt),
            "system_sha256": _sha256(system) if system else None,
            "response_sha256": _sha256(result["content"]),
            "prompt_tokens": result.get("prompt_tokens"),
            "eval_tokens": result.get("eval_tokens"),
            "duration_ms": result.get("duration_ms"),
            "previous_record_hash_sha256": self._previous_hash(),
        }
        record["record_hash_sha256"] = _sha256(_canonical(record))

        # Local append is mandatory: no audit record, no successful call.
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical(record) + "\n")

        ledger_receipt: dict[str, Any] | None = None
        if self.ledger_url:
            ledger_receipt = publish_event(
                {
                    "tenant_id": self.tenant_id,
                    "idempotency_key": f"llm-{record['record_hash_sha256'][:32]}",
                    "event_type": "llm.call.completed",
                    "resource_type": "llm_call_record",
                    "resource_id_pseudonymous": f"call-{record['record_hash_sha256'][:16]}",
                    # Hashes and telemetry only — never raw prompt/response.
                    "payload": record,
                },
                self.ledger_url,
            )

        return {"content": result["content"], "audit_record": record, "ledger_receipt": ledger_receipt}
