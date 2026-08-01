"""Estimated execution cost telemetry; no provider call is made here."""

from __future__ import annotations

from typing import Any

from asus_theye.audit import AuditLedger


def collect_cost_telemetry(
    *,
    shots: int,
    execution_time_ms: float,
    backend: str,
    ibm_cost: float | None = None,
    ledger: AuditLedger | None = None,
) -> dict[str, Any]:
    is_hardware = backend.startswith("ibm_")
    qpu_time_ms = execution_time_ms if is_hardware else 0.0
    record = {
        "estimated_cost": 0.0 if not is_hardware else ibm_cost,
        "currency": "USD",
        "shots": int(shots),
        "qpu_time_ms": qpu_time_ms,
        "ibm_cost": ibm_cost,
        "backend": backend,
        "estimate_only": True,
    }
    if ledger:
        ledger.append("telemetry.cost", record)
    return record
