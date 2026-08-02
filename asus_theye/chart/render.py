"""Renderização do Mistress Chart em texto e HTML."""

from __future__ import annotations

import html
from typing import Any

BAR_WIDTH = 24


def _bar(pct: int, width: int = BAR_WIDTH) -> str:
    filled = round(width * pct / 100)
    return "█" * filled + "·" * (width - filled)


def render_text(snapshot: dict[str, Any], snapshot_hash: str) -> str:
    totals = snapshot["totals"]
    ledger = snapshot["ledger"]
    lines = [
        "=" * 72,
        "MISTRESS CHART — THE EYE",
        "=" * 72,
        f"commit {snapshot['commit']}  ·  {snapshot['generated_at']}",
        f"hash do snapshot: {snapshot_hash}",
        "",
        f"projetos: {totals['projects']}  ({totals['projects_complete']} completos)",
        f"testes:   {totals['tests']}",
        f"nichos:   {totals['niches_covered']}/{totals['niches_total']} "
        f"({totals['niche_coverage_pct']}%)  {_bar(totals['niche_coverage_pct'])}",
        f"cadeia:   {ledger['events']} eventos (topo: sequência {ledger['head_sequence']})",
        "",
        "PROJETOS (medidos por artefato existente, não por status declarado)",
        "-" * 72,
    ]
    for project in sorted(
        snapshot["projects"], key=lambda p: (-p["evidence"]["completion_pct"], p["project_id"])
    ):
        evidence = project["evidence"]
        pct = evidence["completion_pct"]
        lines.append(
            f"  {project['release_class']:3s} {project['project_id']:20s} "
            f"{_bar(pct, 16)} {pct:3d}%  "
            f"{evidence['artifacts_present']}/{evidence['artifacts_declared']} artefatos"
        )
        if evidence["artifacts_missing"]:
            for missing in evidence["artifacts_missing"][:3]:
                lines.append(f"        falta: {missing}")

    lines += ["", "COBERTURA POR GRUPO DE NICHO", "-" * 72]
    for group, counts in snapshot["group_coverage"].items():
        pct = round(100 * counts["covered"] / counts["areas"]) if counts["areas"] else 0
        lines.append(
            f"  {group:34s} {counts['covered']:3d}/{counts['areas']:3d}  {_bar(pct, 12)} {pct:3d}%"
        )

    if ledger["event_types"]:
        lines += ["", "EVENTOS NA CADEIA", "-" * 72]
        for event_type, count in ledger["event_types"].items():
            lines.append(f"  {event_type:36s} {count}")

    lines += ["", "=" * 72]
    return "\n".join(lines)


def render_html(snapshot: dict[str, Any], snapshot_hash: str) -> str:
    totals = snapshot["totals"]
    ledger = snapshot["ledger"]

    def card(label: str, value: str) -> str:
        return (
            f'<div class="card"><div class="label">{html.escape(label)}</div>'
            f'<div class="value">{html.escape(value)}</div></div>'
        )

    rows = []
    for project in sorted(
        snapshot["projects"], key=lambda p: (-p["evidence"]["completion_pct"], p["project_id"])
    ):
        evidence = project["evidence"]
        pct = evidence["completion_pct"]
        missing = ", ".join(evidence["artifacts_missing"][:4]) or "—"
        rows.append(
            "<tr>"
            f'<td><span class="tag">{html.escape(project["release_class"])}</span></td>'
            f"<td><strong>{html.escape(project['name'])}</strong><br>"
            f'<span class="muted">{html.escape(project["purpose"])}</span></td>'
            f'<td class="num">{evidence["artifacts_present"]}/{evidence["artifacts_declared"]}</td>'
            f'<td class="barcell"><div class="track"><div class="fill" style="width:{pct}%"></div>'
            f'</div><span class="pct">{pct}%</span></td>'
            f'<td class="muted small">{html.escape(missing)}</td>'
            "</tr>"
        )

    group_rows = []
    for group, counts in snapshot["group_coverage"].items():
        pct = round(100 * counts["covered"] / counts["areas"]) if counts["areas"] else 0
        group_rows.append(
            "<tr>"
            f"<td>{html.escape(group)}</td>"
            f'<td class="num">{counts["covered"]}/{counts["areas"]}</td>'
            f'<td class="barcell"><div class="track"><div class="fill" style="width:{pct}%"></div>'
            f'</div><span class="pct">{pct}%</span></td>'
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mistress Chart — THE EYE</title>
<style>
 :root {{ color-scheme: dark; }}
 body {{ margin:0; padding:2rem; background:#080b12; color:#e6edf7;
        font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif; }}
 h1 {{ margin:0 0 .25rem; font-size:1.6rem; letter-spacing:.02em; }}
 .sub {{ color:#7d8aa0; font-size:.82rem; font-family:ui-monospace,monospace;
         word-break:break-all; margin-bottom:1.5rem; }}
 .cards {{ display:grid; gap:.75rem; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
           margin-bottom:1.5rem; }}
 .card {{ background:#0f1520; border:1px solid #1d2735; border-radius:10px; padding:.9rem 1rem; }}
 .label {{ color:#7d8aa0; font-size:.68rem; letter-spacing:.09em; text-transform:uppercase; }}
 .value {{ color:#5ad9e8; font-size:1.5rem; font-weight:600; margin-top:.2rem; }}
 h2 {{ font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:#7d8aa0;
       margin:2rem 0 .6rem; }}
 table {{ width:100%; border-collapse:collapse; background:#0f1520;
          border:1px solid #1d2735; border-radius:10px; overflow:hidden; }}
 th {{ text-align:left; font-size:.68rem; letter-spacing:.09em; text-transform:uppercase;
       color:#7d8aa0; padding:.6rem .8rem; border-bottom:1px solid #1d2735; font-weight:500; }}
 td {{ padding:.65rem .8rem; border-bottom:1px solid #161f2c; vertical-align:top; }}
 tr:last-child td {{ border-bottom:none; }}
 .num {{ font-family:ui-monospace,monospace; color:#9fb0c8; white-space:nowrap; }}
 .muted {{ color:#7d8aa0; }} .small {{ font-size:.78rem; }}
 .tag {{ background:#16233a; color:#5ad9e8; border-radius:5px; padding:.12rem .45rem;
         font-size:.72rem; font-family:ui-monospace,monospace; }}
 .barcell {{ white-space:nowrap; width:150px; }}
 .track {{ display:inline-block; width:96px; height:7px; background:#16202e;
           border-radius:4px; overflow:hidden; vertical-align:middle; }}
 .fill {{ height:100%; background:linear-gradient(90deg,#2f8fd8,#5ad9e8); }}
 .pct {{ font-family:ui-monospace,monospace; font-size:.78rem; color:#9fb0c8;
         margin-left:.5rem; }}
 footer {{ margin-top:2rem; color:#5c6880; font-size:.75rem; }}
</style></head><body>
<h1>Mistress Chart</h1>
<div class="sub">commit {html.escape(snapshot['commit'])} · {html.escape(snapshot['generated_at'])}<br>
snapshot sha256: {html.escape(snapshot_hash)}</div>
<div class="cards">
{card("Projetos", str(totals["projects"]))}
{card("Completos", str(totals["projects_complete"]))}
{card("Testes", str(totals["tests"]))}
{card("Nichos cobertos", f"{totals['niches_covered']}/{totals['niches_total']}")}
{card("Eventos na cadeia", str(ledger["events"]))}
</div>
<h2>Projetos — medidos por artefato existente</h2>
<table><thead><tr><th>Classe</th><th>Projeto</th><th>Artefatos</th><th>Progresso</th>
<th>Faltando</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<h2>Cobertura por grupo de nicho</h2>
<table><thead><tr><th>Grupo</th><th>Cobertos</th><th>Progresso</th></tr></thead>
<tbody>{"".join(group_rows)}</tbody></table>
<footer>Todo número desta página é derivado de evidência verificável — arquivos que
existem, testes coletados, commits, eventos encadeados. Nenhum status é
autodeclarado. O hash acima é ancorado no ledger.</footer>
</body></html>
"""
