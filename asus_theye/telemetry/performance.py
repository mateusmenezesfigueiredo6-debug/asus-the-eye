"""Portable process performance telemetry."""

from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from typing import Any

from asus_theye import __version__
from asus_theye.audit import AuditLedger


def collect_performance_telemetry(
    *, execution_time_ms: float, execution: str, ledger: AuditLedger | None = None
) -> dict[str, Any]:
    cpu_percent: float | None = None
    ram_mb: float | None = None
    try:
        import psutil

        process = psutil.Process(os.getpid())
        cpu_percent = process.cpu_percent(interval=None)
        ram_mb = process.memory_info().rss / (1024 * 1024)
    except ImportError:
        pass
    record = {
        "cpu_percent": cpu_percent,
        "ram_mb": ram_mb,
        "execution_time_ms": float(execution_time_ms),
        "execution": execution,
        "version": __version__,
        "python_version": platform.python_version(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if ledger:
        ledger.append("telemetry.performance", record)
    return record
