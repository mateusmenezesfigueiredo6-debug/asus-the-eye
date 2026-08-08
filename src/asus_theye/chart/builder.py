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

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "data" / "mistress-chart" / "projects.json"
TAXONOMY_PATH = REPO_ROOT / "data" / "legal-taxonomy" / "legal_areas.master.json"
DOMAINS_PATH = REPO_ROOT / "data" / "domains" / "domains.json"

# Compatibilidade com o registro anterior, que nao tinha dominio: projeto sem
# `domain_id` conta como direito. E divida a pagar, nao desenho — enquanto
# existir, um projeto de outro assunto pode entrar no denominador errado por
# esquecimento.
DOMINIO_PADRAO = "direito"


def _load_domains() -> dict[str, dict[str, Any]]:
    """Carrega o classificador de cada dominio.

    Ate 08/08/2026 esta funcao nao existia e `areas` vinha so da taxonomia
    juridica, de modo que `niches_total` era `len(areas juridicas)` e qualquer
    projeto so conseguia declarar escopo em vocabulario de direito — inclusive
    o source-graph, cuja missao e mapear inovacao em IA e computacao quantica.
    A taxonomia legal tinha virado a taxonomia da plataforma por omissao.

    Dominio cujo classificador nao existe em disco e ignorado com as areas
    vazias, nunca silenciosamente fundido com outro: preferimos denominador
    faltando a denominador errado.
    """
    if not DOMAINS_PATH.exists():
        return {}
    registro = json.loads(DOMAINS_PATH.read_text(encoding="utf-8"))
    dominios: dict[str, dict[str, Any]] = {}
    for d in registro.get("domains", []):
        caminho = REPO_ROOT / d["classifier"]
        areas: dict[str, dict[str, Any]] = {}
        if caminho.exists():
            bruto = json.loads(caminho.read_text(encoding="utf-8"))
            for area in bruto.get(d.get("collection", "areas"), []):
                chave = area.get(d["id_field"])
                if chave:
                    areas[chave] = area
        dominios[d["domain_id"]] = {
            **d,
            "areas": areas,
            "classifier_found": caminho.exists(),
        }
    return dominios


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
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
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
    present: list[str] = []
    missing: list[str] = []
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
        "last_commit": _git(["log", "-1", "--format=%h %ad", "--date=short", "--", *project.get("paths", ["."])]),
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


def _knowledge_section() -> dict[str, Any]:
    """Painel de navegação do grafo de fontes: onde estamos em cada trilha.

    Lê os registries de data/source-graph/ e a cobertura calculada. No dia 1 tudo
    aparece com blocking_reason 'not_yet_attempted' — o painel mostra o que
    existe, não o que se pretende.
    """
    source_graph_dir = REPO_ROOT / "data" / "source-graph"
    if not source_graph_dir.exists():
        return {"available": False, "reason": "data/source-graph ainda não existe"}

    from asus_theye.source_graph.coverage import build_coverage, coverage_by_track

    def load(name: str) -> dict[str, Any]:
        return json.loads((source_graph_dir / name).read_text(encoding="utf-8"))

    connectors = load("connectors.json")["connectors"]
    artifacts = load("software_artifacts.json")["artifacts"]
    communities = load("communities.json")["communities"]

    # As fontes descobertas vivem em sources.json. Passar [] aqui fazia o chart
    # publicar 0,0% enquanto o relatorio de cobertura ja mostrava 13,4% — o
    # mesmo defeito existia no CLI e foi corrigido em 829847e.
    fontes_path = source_graph_dir / "sources.json"
    fontes = json.loads(fontes_path.read_text(encoding="utf-8")).get("sources", []) if fontes_path.exists() else []
    coverage = build_coverage(fontes)

    by_poc: dict[str, int] = {}
    for artifact in artifacts:
        by_poc[artifact["poc_status"]] = by_poc.get(artifact["poc_status"], 0) + 1

    return {
        "available": True,
        "methodology_version": coverage["methodology_version"],
        "sources_loaded": len(fontes),
        "sources_pending_human_review": sum(1 for f in fontes if f.get("human_review", {}).get("status") == "pending"),
        "tracks": coverage_by_track(coverage),
        "connectors": {
            "declared": len(connectors),
            "enabled": sum(1 for c in connectors if c.get("enabled")),
            "blocked_by_cost_or_key": sum(1 for c in connectors if c.get("requires_key")),
        },
        "artifacts": {
            "declared": len(artifacts),
            "by_poc_status": dict(sorted(by_poc.items())),
            "verified": sum(1 for a in artifacts if a.get("verification_status") == "verified"),
        },
        "communities": {"declared": len(communities)},
        "gaps": coverage["gaps"],
        "coverage_snapshot_hash": coverage["snapshot_hash_sha256"],
    }


def build_chart(ledger_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    areas = {area["legal_area_id"]: area for area in taxonomy["areas"]}

    dominios = _load_domains()
    # Sem registro de dominios o comportamento antigo continua valendo, para
    # que o chart nunca dependa de um arquivo novo para rodar.
    if not dominios:
        dominios = {
            DOMINIO_PADRAO: {"domain_id": DOMINIO_PADRAO, "name": "Direito", "areas": areas, "classifier_found": True}
        }

    projects = []
    for project in registry["projects"]:
        evidence = _evidence_for(project)
        dom = project.get("domain_id", DOMINIO_PADRAO)
        # O nicho e validado contra o classificador do PROPRIO dominio. Validar
        # contra outro produziria unknown_niches falso ou, pior, um nicho de
        # mercado contado como area de direito.
        conhecidas = dominios.get(dom, {}).get("areas", {})
        unknown = [n for n in project.get("niches", []) if n not in conhecidas and n != "*"]
        projects.append(
            {
                **project,
                "domain_id": dom,
                "evidence": evidence,
                "unknown_niches": unknown,
            }
        )

    # Cobertura por nicho, agora por dominio: qual area tem ao menos um projeto.
    # A chave e (dominio, area) porque dois dominios podem ter ids homonimos.
    covered: dict[str, list[str]] = {}
    covered_por_dominio: dict[str, set[str]] = {d: set() for d in dominios}
    for project in projects:
        dom = project["domain_id"]
        for niche in project.get("niches", []):
            if niche == "*":
                continue
            covered.setdefault(niche, []).append(project["project_id"])
            covered_por_dominio.setdefault(dom, set()).add(niche)

    domain_coverage = {}
    for did, d in dominios.items():
        total = len(d["areas"])
        cob = len(covered_por_dominio.get(did, set()) & set(d["areas"]))
        domain_coverage[did] = {
            "name": d.get("name", did),
            "areas_total": total,
            "areas_covered": cob,
            "coverage_pct": round(100 * cob / total, 1) if total else 0.0,
            # Este numero mede DECLARACAO, nao dado processado: uma area conta
            # como coberta porque algum projeto a listou no campo `niches`, e
            # sobe se alguem editar um JSON. Coberto NAO significa que exista
            # lead extraido, fonte no grafo ou mercado resolvido naquela area.
            # O rotulo viaja junto com o numero para que nenhum painel possa
            # apresenta-lo como medicao sem estar mentindo por escrito.
            "coverage_kind": "declared",
            "coverage_caveat": (
                "cobertura declarada: conta area listada em projects.json, nao area com dado processado"
            ),
            "classifier_found": d.get("classifier_found", False),
            "projects": sorted(p["project_id"] for p in projects if p["domain_id"] == did),
        }

    areas_todas = sum(len(d["areas"]) for d in dominios.values())
    cobertas_todas = sum(v["areas_covered"] for v in domain_coverage.values())

    groups: dict[str, dict[str, int]] = {}
    for area_id, area in areas.items():
        group_bucket = groups.setdefault(area["group"], {"areas": 0, "covered": 0})
        group_bucket["areas"] += 1
        if area_id in covered:
            group_bucket["covered"] += 1

    # O projeto inteiro como UM pipeline, medido etapa por etapa.
    stages: dict[str, dict[str, Any]] = {}
    for project in projects:
        stage = project.get("pipeline_stage", "sem-etapa")
        evidence = project["evidence"]
        stage_bucket: dict[str, Any] = stages.setdefault(
            stage,
            {
                "order": project.get("pipeline_order", 99),
                "projects": [],
                "artifacts_present": 0,
                "artifacts_declared": 0,
                "release_classes": set(),
            },
        )
        stage_bucket["projects"].append(project["project_id"])
        stage_bucket["artifacts_present"] += evidence["artifacts_present"]
        stage_bucket["artifacts_declared"] += evidence["artifacts_declared"]
        stage_bucket["release_classes"].add(project["release_class"])
    for stage_bucket in stages.values():
        declared = stage_bucket["artifacts_declared"]
        stage_bucket["completion_pct"] = round(100 * stage_bucket["artifacts_present"] / declared) if declared else 0
        stage_bucket["release_classes"] = sorted(stage_bucket["release_classes"])
    pipeline = dict(sorted(stages.items(), key=lambda item: item[1]["order"]))

    snapshot = {
        "chart_version": registry.get("chart_version", "1.0.0"),
        "pipeline": pipeline,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "commit": _git(["rev-parse", "--short", "HEAD"]),
        "knowledge": _knowledge_section(),
        "totals": {
            "projects": len(projects),
            "projects_complete": sum(1 for p in projects if p["evidence"]["completion_pct"] == 100),
            "tests": _count_tests(),
            # O denominador agora soma TODOS os dominios. Antes era so o
            # juridico, o que fazia a cobertura da plataforma inteira ser
            # reportada como fracao de 145 areas de direito.
            "niches_total": areas_todas,
            "niches_covered": cobertas_todas,
            "niche_coverage_pct": round(100 * cobertas_todas / areas_todas) if areas_todas else 0,
            "domains_total": len(dominios),
            "domains_with_coverage": sum(1 for v in domain_coverage.values() if v["areas_covered"]),
        },
        "ledger": _ledger_evidence(ledger_events),
        "projects": projects,
        "niche_coverage": {area_id: sorted(ids) for area_id, ids in sorted(covered.items())},
        "group_coverage": dict(sorted(groups.items())),
        "domain_coverage": dict(sorted(domain_coverage.items())),
    }
    return snapshot


def chart_snapshot_hash(snapshot: dict[str, Any]) -> str:
    """Hash do snapshot ignorando o carimbo de tempo (dois runs iguais = mesmo hash)."""
    stable = {key: value for key, value in snapshot.items() if key != "generated_at"}
    return hashlib.sha256(_canonical(stable).encode("utf-8")).hexdigest()
