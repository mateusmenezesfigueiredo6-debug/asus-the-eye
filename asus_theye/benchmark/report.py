"""Atomic benchmark report generation and neutral conclusions."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def neutral_conclusion(results: dict[str, dict[str, Any]], metrics: dict[str, Any]) -> str:
    classical = results["classical"]
    qaoa = results["qaoa"]
    if classical["score"] >= qaoa["score"]:
        return "Classical solver achieved equal or better quality under the current problem size."
    return (
        "QAOA produced a higher score in this local simulation; repeated experiments and "
        "statistical validation are required before any quantum-advantage claim."
    )


def build_report(
    *, problem: dict[str, Any], results: dict[str, dict[str, Any]], metrics: dict[str, Any]
) -> dict[str, Any]:
    return {
        "project": "ASUS THE EYE",
        "engine_version": "0.2.0",
        "date": datetime.now(timezone.utc).isoformat(),
        "problem": problem,
        "results": results,
        "metrics": metrics,
        "conclusion": neutral_conclusion(results, metrics),
        "limitations": [
            "QAOA result uses a controlled local simulator, not a real QPU.",
            "A single demo problem cannot establish general performance or quantum advantage.",
            "Wall-clock measurements depend on the local machine and concurrent workload.",
        ],
    }


def write_report(report: dict[str, Any], path: str | Path) -> Path:
    """Write JSON atomically, avoiding partial reports on interruption."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".benchmark-", suffix=".json", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return destination
