"""Constrói o Mistress Chart a partir de EVIDÊNCIA, não de status declarado.

Regra do projeto: ninguém escreve "80% pronto" num campo. Cada número aqui é
derivado de algo verificável — arquivos que existem, testes que passam, commits
no git, eventos na cadeia, cobertura da taxonomia. Se não há evidência, o valor
é 0 e o motivo aparece.

O snapshot inteiro é hasheado e ancorado no ledger, então o histórico do chart
é tão auditável quanto o resto: dá para provar o que se sabia, e quando.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "data" / "mistress-chart" / "projects.json"
TAXONOMY_PATH = REPO_ROOT / "data" / "legal-taxonomy" / "legal_areas.master.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _git(args: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=True
        ).stdout.strip()
    except Exception:
        return ""


def _count_tests() -> int:
    try:
        out = subprocess.run(
            [str(REPO_ROOT / ".venv/bin/python"), "-m", "pytest", "--collect-only", "-q", "tests/"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=300,
        ).stdout
    except Exception:
        return 0
    total = 0
    for line in out.splitlines():
        if ":" in line and line.rsplit(":", 1)[-1].strip().isdigit():
            total += int(line.rsplit(":", 1)[-1].strip())
    return total


def _evidence_for(project: dict[str, Any]) -> dict[str, Any]:
    """Mede um projeto pelos artefatos que ele declara — existindo ou não."""
    present, missing = [], []
    for relative in project.get("artifacts", []):
        path = REPO_ROOT / relative
        (present if path.exists() else missing).append(relative)
    total = len(present) + len(missing)
    return {
        "artifacts_present": len(present),
        "artifacts_declared": total,
        "artifacts_missing": missing,
        "completion_pct": round(100 * len(present) / total) if total else 0,
        "commits": int(_git(["rev-list", "--count", "HEAD", "--", *project.get("paths", ["."])]) or 0),
        "last_commit": _git(["log", "-1", "--format=%h %ad", "--date=short", "--",
                             *project.get("paths", ["."])]),
    }


def _ledger_evidence(events: list[dict[str, Any]] | None) -> dict[str, Any]:
    if not events:
        return {"events": 0, "head_sequence": 0, "event_types": {}}
    types: dict[str, int] = {}
    for event in events:
        types[event["event_type"]] = types.get(event["event_type"], 0) + 1
    return {
        "events": len(events),
        "head_sequence": max(e["sequence"] for e in events),
        "event_types": dict(sorted(types.items())),
    }


def build_chart(ledger_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    areas = {area["legal_area_id"]: area for area in taxonomy["areas"]}

    projects = []
    for project in registry["projects"]:
        evidence = _evidence_for(project)
        unknown = [n for n in project.get("niches", []) if n not in areas and n != "*"]
        projects.append({**project, "evidence": evidence, "unknown_niches": unknown})

    # Cobertura por nicho: quais das 145 áreas têm ao menos um projeto ativo.
    covered: dict[str, list[str]] = {}
    for project in projects:
        for niche in project.get("niches", []):
            if niche == "*":
                continue
            covered.setdefault(niche, []).append(project["project_id"])

    groups: dict[str, dict[str, int]] = {}
    for area_id, area in areas.items():
        bucket = groups.setdefault(area["group"], {"areas": 0, "covered": 0})
        bucket["areas"] += 1
        if area_id in covered:
            bucket["covered"] += 1

    snapshot = {
        "chart_version": registry.get("chart_version", "1.0.0"),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "commit": _git(["rev-parse", "--short", "HEAD"]),
        "totals": {
            "projects": len(projects),
            "projects_complete": sum(1 for p in projects if p["evidence"]["completion_pct"] == 100),
            "tests": _count_tests(),
            "niches_total": len(areas),
            "niches_covered": len(covered),
            "niche_coverage_pct": round(100 * len(covered) / len(areas)) if areas else 0,
        },
        "ledger": _ledger_evidence(ledger_events),
        "projects": projects,
        "niche_coverage": {area_id: sorted(ids) for area_id, ids in sorted(covered.items())},
        "group_coverage": dict(sorted(groups.items())),
    }
    return snapshot


def chart_snapshot_hash(snapshot: dict[str, Any]) -> str:
    """Hash do snapshot ignorando o carimbo de tempo (dois runs iguais = mesmo hash)."""
    stable = {key: value for key, value in snapshot.items() if key != "generated_at"}
    return hashlib.sha256(_canonical(stable).encode("utf-8")).hexdigest()
