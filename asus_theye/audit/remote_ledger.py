"""Publish benchmark evidence to the remote staging audit ledger.

Standard library only. Publishing is strictly opt-in (``--publish``): the
benchmark never phones home by default. The idempotency key is derived from the
report content, so re-publishing the same report is a no-op on the ledger
(the worker answers with the original event instead of appending).
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_TENANT = "tenant-demo"
_TIMEOUT_SECONDS = 30
_TOKEN_FILE = Path.home() / ".the-eye" / "staging-token"


def _ledger_token() -> str | None:
    """Bearer token for the restricted ledger: env var wins, then key file."""
    token = os.environ.get("THE_EYE_LEDGER_TOKEN")
    if token:
        return token.strip()
    if _TOKEN_FILE.exists():
        return _TOKEN_FILE.read_text(encoding="utf-8").strip()
    return None


class LedgerPublishError(RuntimeError):
    """Raised when the remote ledger rejects or fails to store the event."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_benchmark_event(report: dict[str, Any], tenant_id: str = DEFAULT_TENANT) -> dict[str, Any]:
    """Map a benchmark report to an audit ingest body.

    Only aggregate, non-personal engine telemetry is published. The full report
    stays local; the ledger stores the summary plus the report content hash so
    the local file can later be proven against the chain.
    """
    report_hash = hashlib.sha256(_canonical(report).encode("utf-8")).hexdigest()
    results = report.get("results", {})
    metrics = report.get("metrics", {})
    qaoa = results.get("qaoa", {})
    summary = {
        "engine_version": report.get("engine_version"),
        "problem": report.get("problem", {}).get("name"),
        "classical_score": results.get("classical", {}).get("score"),
        "qubo_score": results.get("qubo", {}).get("score"),
        "qaoa_score": qaoa.get("score"),
        "qaoa_backend": qaoa.get("backend"),
        "hardware_execution": qaoa.get("hardware_execution", False),
        "qar": metrics.get("qar", {}).get("qar"),
        "report_generated_at": report.get("date"),
        "report_hash_sha256": report_hash,
    }
    return {
        "tenant_id": tenant_id,
        "idempotency_key": f"benchmark-{report_hash[:32]}",
        "event_type": "benchmark.completed",
        "resource_type": "benchmark_report",
        "resource_id_pseudonymous": f"report-{report_hash[:16]}",
        "payload": summary,
    }


def publish_event(body: dict[str, Any], ledger_url: str) -> dict[str, Any]:
    """POST an audit ingest body to ``<ledger_url>/events`` and return the receipt.

    Fails loudly (:class:`LedgerPublishError`) — per the critical-mutation rule,
    a publish that cannot be recorded must never look successful.
    """
    headers = {
        "content-type": "application/json",
        # Cloudflare's browser integrity check rejects the default
        # Python-urllib user agent with error 1010.
        "user-agent": "asus-theye-audit-client/0.2",
    }
    token = _ledger_token()
    if token:
        headers["authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{ledger_url.rstrip('/')}/events",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            receipt = json.loads(response.read().decode("utf-8"))
            status = response.status
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise LedgerPublishError(f"ledger rejected event: HTTP {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise LedgerPublishError(f"ledger unreachable: {error}") from error
    if status not in (200, 201):
        raise LedgerPublishError(f"unexpected ledger status {status}: {receipt}")
    return receipt


def publish_benchmark_report(
    report: dict[str, Any],
    ledger_url: str,
    tenant_id: str = DEFAULT_TENANT,
) -> dict[str, Any]:
    """Publish a benchmark report summary to the remote ledger."""
    return publish_event(build_benchmark_event(report, tenant_id), ledger_url)
