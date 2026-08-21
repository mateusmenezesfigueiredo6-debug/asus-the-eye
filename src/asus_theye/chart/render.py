# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Renderização do Mistress Chart em texto e HTML."""

from __future__ import annotations

import html
from typing import Any

BAR_WIDTH = 24


def _bar(pct: int | None, width: int = BAR_WIDTH) -> str:
    """A barra — ou uma faixa vazia quando não houve medição.

    ``None`` não é 0%. Desenhar barra vazia para um número que não existe seria
    a mesma mentira que o zero fabricado, só que em ASCII.
    """
    if pct is None:
        return "?" * width
    filled = round(width * pct / 100)
    return "█" * filled + "·" * (width - filled)


def _pct(pct: float | None, largura: int = 3) -> str:
    """Percentual, ou travessão. Nunca imprime 'None'.

    Aceita ``float`` porque a cobertura por domínio é fracionária, enquanto a
    conclusão por projeto é inteira — e as duas passam por aqui. Um formatador
    só, que não quebra conforme o tipo, evita a próxima vez que alguém trocar o
    tipo de um campo e derrubar o painel.
    """
    if pct is None:
        return "—".rjust(largura)
    if isinstance(pct, float) and not pct.is_integer():
        return f"{pct:.1f}"
    return f"{int(pct):{largura}d}"


def _num(valor: Any) -> str:
    return "—" if valor is None else str(valor)


def _pct_css(pct: int | None) -> str:
    """Largura da barra no HTML. Sem medição, barra vazia — e o rótulo diz —."""
    return "0%" if pct is None else f"{pct}%"


STAGE_LABELS = {
    "1-ingestao": "Ingestão — descobrir e hashear fontes",
    "2-classificacao": "Classificação — 145 nichos, extração validada",
    "3-processamento": "Processamento — benchmark, LLM local, QPU",
    "4-operacao": "Operação — funil comercial, 15 nichos",
    "5-evidencia": "Evidência — hash chain, Merkle, ledger vivo",
    "6-verificacao": "Verificação — governança, contrato de ancoragem",
    "7-publicacao": "Publicação — superfície pública (nada publicado)",
}


def _pipeline_text(pipeline: dict[str, Any]) -> list[str]:
    lines = ["", "PIPELINE — o projeto inteiro, etapa por etapa", "-" * 72]
    for stage, data in pipeline.items():
        pct = data["completion_pct"]
        label = STAGE_LABELS.get(stage, stage)
        classes = "/".join(data["release_classes"])
        lines.append(
            f"  {stage:17s} {_bar(pct, 14)} {_pct(pct)}%  "
            f"{_num(data['artifacts_present']):>3s}/{data['artifacts_declared']:<3d}  [{classes}]"
        )
        lines.append(f"      {label}")
        lines.append(f"      {', '.join(data['projects'])}")
    return lines


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
        f"projetos: {totals['projects']}  ({_num(totals['projects_complete'])} completos)",
        f"testes:   {_num(totals['tests'])}",
        f"nichos:   {totals['niches_covered']}/{totals['niches_total']} "
        f"({totals['niche_coverage_pct']}%)  {_bar(totals['niche_coverage_pct'])}",
        f"cadeia:   {ledger['events']} eventos (topo: sequência {ledger['head_sequence']})",
        "",
    ]
    if snapshot.get("medicao_impossivel"):
        lines += [
            "!" * 72,
            "  ATENÇÃO — este painel NÃO foi medido.",
            f"  {snapshot['medicao_impossivel']}",
            "  Os percentuais aparecem como — porque não existem, não porque são zero.",
            "!" * 72,
            "",
        ]
    lines += _pipeline_text(snapshot.get("pipeline", {}))
    lines += [
        "",
        "PROJETOS (medidos por artefato existente, não por status declarado)",
        "-" * 72,
    ]
    # Projeto sem medição vai para o fim, e não para o topo com 100% nem para
    # o fundo com 0% — os dois lugares afirmariam algo que não foi medido.
    for project in sorted(
        snapshot["projects"],
        key=lambda p: (
            p["evidence"]["completion_pct"] is None,
            -(p["evidence"]["completion_pct"] or 0),
            p["project_id"],
        ),
    ):
        evidence = project["evidence"]
        pct = evidence["completion_pct"]
        lines.append(
            f"  {project['release_class']:3s} {project['project_id']:20s} "
            f"{_bar(pct, 16)} {_pct(pct)}%  "
            f"{_num(evidence['artifacts_present'])}/{evidence['artifacts_declared']} artefatos"
        )
        if evidence.get("medicao_impossivel"):
            lines.append(f"        {evidence['medicao_impossivel']}")
        if evidence["artifacts_missing"]:
            for missing in evidence["artifacts_missing"][:3]:
                lines.append(f"        falta: {missing}")

    lines += ["", "COBERTURA POR GRUPO DE NICHO", "-" * 72]
    for group, counts in snapshot["group_coverage"].items():
        pct = round(100 * counts["covered"] / counts["areas"]) if counts["areas"] else 0
        lines.append(f"  {group:34s} {counts['covered']:3d}/{counts['areas']:3d}  {_bar(pct, 12)} {pct:3d}%")

    knowledge = snapshot.get("knowledge", {})
    if knowledge.get("available"):
        lines += ["", "GRAFO DE FONTES — TRILHAS", "-" * 72]
        for track, data in knowledge["tracks"].items():
            pct = data["coverage_pct"]
            reasons = ", ".join(f"{k}×{v}" for k, v in sorted(data["blocking_reasons"].items()))
            lines.append(
                f"  {track:14s} {data['qualified']:4d}/{data['target']:5d}  "
                f"{_bar(int(pct), 12)} {pct:5.1f}%  [{reasons}]"
            )
        connectors = knowledge["connectors"]
        artifacts = knowledge["artifacts"]
        lines += [
            "",
            f"  conectores:   {connectors['declared']} declarados, "
            f"{connectors['enabled']} habilitados, "
            f"{connectors['blocked_by_cost_or_key']} bloqueados por chave/custo",
            f"  bibliotecas:  {artifacts['declared']} declaradas "
            f"({', '.join(f'{k}={v}' for k, v in artifacts['by_poc_status'].items())}), "
            f"{artifacts['verified']} verificadas",
            f"  comunidades:  {knowledge['communities']['declared']} declaradas",
            "",
            "  LACUNAS (cada uma com o que a destravaria)",
        ]
        for gap in knowledge["gaps"]:
            lines.append(f"    [{gap['blocking_reason']}] {gap['description']}")
            lines.append(f"        → {gap.get('what_would_unblock', '')}")

    if ledger["event_types"]:
        lines += ["", "EVENTOS NA CADEIA", "-" * 72]
        for event_type, count in ledger["event_types"].items():
            lines.append(f"  {event_type:36s} {count}")

    lines += ["", "=" * 72]
    return "\n".join(lines)


TRACK_LABELS = {
    "fundacao": "Fundação — periódicos, datasets oficiais, associações, conferências",
    "academico": "Acadêmico — universidades, centros de pesquisa, observatórios",
    "setorial": "Setorial — reguladores, tribunais, instituições, veículos",
    "gated_dpia": "Bloqueado por DPIA — categorias que descrevem pessoas (L4)",
    "outros": "Outros",
}

REASON_LABELS = {
    "none": "coberto",
    "not_yet_attempted": "ainda não tentado",
    "requires_dpia": "exige DPIA humana",
    "requires_paid_api": "exige fonte paga",
    "license_restricted": "licença restringe",
    "robots_disallowed": "robots proíbe",
    "no_free_source": "não existe fonte gratuita",
}


def _mermaid_graph(knowledge: dict[str, Any]) -> str:
    """Diagrama do grafo: trilhas → estado, com o motivo do bloqueio visível."""
    lines = ["graph LR", "  GRAFO[Grafo de fontes]"]
    for index, (track, data) in enumerate(knowledge["tracks"].items()):
        node = f"T{index}"
        label = track.replace("_", " ")
        lines.append(f'  GRAFO --> {node}["{label}<br/>{data["qualified"]}/{data["target"]}"]')
        for reason, count in sorted(data["blocking_reasons"].items()):
            reason_node = f"{node}R{abs(hash(reason)) % 1000}"
            text = REASON_LABELS.get(reason, reason)
            arrow = "-->" if reason == "none" else "-.->"
            lines.append(f'  {node} {arrow} {reason_node}["{text}<br/>{count} categoria(s)"]')
    return "\n".join(lines)


def _pipeline_html(pipeline: dict[str, Any]) -> str:
    """O projeto como um pipeline: barras por etapa + diagrama do fluxo."""
    if not pipeline:
        return ""

    rows = []
    for stage, data in pipeline.items():
        pct = data["completion_pct"]
        rows.append(
            "<tr>"
            f'<td><span class="tag">{html.escape(stage.split("-")[0])}</span></td>'
            f"<td><strong>{html.escape(STAGE_LABELS.get(stage, stage))}</strong><br>"
            f'<span class="muted small">{html.escape(", ".join(data["projects"]))}</span></td>'
            f'<td class="num">{_num(data["artifacts_present"])}/{data["artifacts_declared"]}</td>'
            f'<td class="barcell"><div class="track"><div class="fill" style="width:{_pct_css(pct)}"></div>'
            f'</div><span class="pct">{_pct(pct, 1).strip()}%</span></td>'
            f'<td class="muted small">{html.escape("/".join(data["release_classes"]))}</td>'
            "</tr>"
        )

    nodes = []
    for index, (stage, data) in enumerate(pipeline.items()):
        short = stage.split("-", 1)[1].replace("-", " ")
        pct = data["completion_pct"]
        nodes.append((f"E{index}", short, pct, _num(data["artifacts_present"]), data["artifacts_declared"]))

    diagram = ["graph LR"]
    for node_id, short, pct, present, declared in nodes:
        diagram.append(f'  {node_id}["{short}<br/>{present}/{declared} · {_pct(pct, 1).strip()}%"]')
    for (a, *_), (b, *_) in zip(nodes, nodes[1:], strict=False):
        diagram.append(f"  {a} --> {b}")
    diagram.append('  E6 -.-> BLOQ["nada publicado<br/>L5 exige senha + 24h"]')

    return f"""
<h2>Pipeline — o projeto inteiro, etapa por etapa</h2>
<table><thead><tr><th>#</th><th>Etapa</th><th>Artefatos</th><th>Progresso</th>
<th>Classe</th></tr></thead><tbody>{"".join(rows)}</tbody></table>

<h2>Fluxo</h2>
<pre class="mermaid">{html.escape(chr(10).join(diagram))}</pre>
"""


def _knowledge_html(knowledge: dict[str, Any]) -> str:
    if not knowledge.get("available"):
        return ""

    track_rows = []
    for track, data in knowledge["tracks"].items():
        pct = data["coverage_pct"]
        reasons = " · ".join(f"{REASON_LABELS.get(k, k)} ×{v}" for k, v in sorted(data["blocking_reasons"].items()))
        track_rows.append(
            "<tr>"
            f"<td><strong>{html.escape(TRACK_LABELS.get(track, track))}</strong></td>"
            f'<td class="num">{data["qualified"]}/{data["target"]}</td>'
            f'<td class="barcell"><div class="track"><div class="fill" style="width:{_pct_css(pct)}"></div>'
            f'</div><span class="pct">{_pct(pct, 1).strip()}%</span></td>'
            f'<td class="muted small">{html.escape(reasons)}</td>'
            "</tr>"
        )

    artifacts = knowledge["artifacts"]
    connectors = knowledge["connectors"]
    poc = ", ".join(f"{k}: {v}" for k, v in artifacts["by_poc_status"].items())
    connector_note = f"{connectors['enabled']} habilitados · {connectors['blocked_by_cost_or_key']} exigem chave/custo"

    gap_rows_list = []
    for gap in knowledge["gaps"]:
        reason = gap["blocking_reason"]
        label = REASON_LABELS.get(reason, reason)
        unblock = gap.get("what_would_unblock") or "—"
        gap_rows_list.append(
            "<tr>"
            f'<td><span class="tag">{html.escape(label)}</span></td>'
            f"<td>{html.escape(gap['description'])}</td>"
            f'<td class="muted small">{html.escape(unblock)}</td>'
            "</tr>"
        )
    gap_rows = "".join(gap_rows_list)

    return f"""
<h2>Grafo de fontes — onde estamos em cada trilha</h2>
<table><thead><tr><th>Trilha</th><th>Qualificadas</th><th>Cobertura</th>
<th>Motivo</th></tr></thead><tbody>{"".join(track_rows)}</tbody></table>

<div class="cards" style="margin-top:1rem">
<div class="card"><div class="label">Conectores</div><div class="value">{connectors["declared"]}</div>
<div class="muted small">{connector_note}</div></div>
<div class="card"><div class="label">Bibliotecas com PoC</div><div class="value">{artifacts["declared"]}</div>
<div class="muted small">{html.escape(poc)}</div></div>
<div class="card"><div class="label">Comunidades</div><div class="value">{knowledge["communities"]["declared"]}</div>
<div class="muted small">registradas como fontes, nunca as pessoas nelas</div></div>
</div>

<h2>Mapa das trilhas</h2>
<pre class="mermaid">{html.escape(_mermaid_graph(knowledge))}</pre>

<h2>Lacunas — e o que destravaria cada uma</h2>
<table><thead><tr><th>Motivo</th><th>Lacuna</th><th>O que destravaria</th></tr></thead>
<tbody>{gap_rows}</tbody></table>
"""


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
        snapshot["projects"],
        key=lambda p: (
            p["evidence"]["completion_pct"] is None,
            -(p["evidence"]["completion_pct"] or 0),
            p["project_id"],
        ),
    ):
        evidence = project["evidence"]
        pct = evidence["completion_pct"]
        missing = ", ".join(evidence["artifacts_missing"][:4]) or "—"
        rows.append(
            "<tr>"
            f'<td><span class="tag">{html.escape(project["release_class"])}</span></td>'
            f"<td><strong>{html.escape(project['name'])}</strong><br>"
            f'<span class="muted">{html.escape(project["purpose"])}</span></td>'
            f'<td class="num">{_num(evidence["artifacts_present"])}/{evidence["artifacts_declared"]}</td>'
            f'<td class="barcell"><div class="track"><div class="fill" style="width:{_pct_css(pct)}"></div>'
            f'</div><span class="pct">{_pct(pct, 1).strip()}%</span></td>'
            f'<td class="muted small">{html.escape(missing)}</td>'
            "</tr>"
        )

    knowledge_block = _knowledge_html(snapshot.get("knowledge", {}))
    pipeline_block = _pipeline_html(snapshot.get("pipeline", {}))

    group_rows = []
    for group, counts in snapshot["group_coverage"].items():
        pct = round(100 * counts["covered"] / counts["areas"]) if counts["areas"] else 0
        group_rows.append(
            "<tr>"
            f"<td>{html.escape(group)}</td>"
            f'<td class="num">{counts["covered"]}/{counts["areas"]}</td>'
            f'<td class="barcell"><div class="track"><div class="fill" style="width:{_pct_css(pct)}"></div>'
            f'</div><span class="pct">{_pct(pct, 1).strip()}%</span></td>'
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
<div class="sub">commit {html.escape(snapshot["commit"])} · {html.escape(snapshot["generated_at"])}<br>
snapshot sha256: {html.escape(snapshot_hash)}</div>
<div class="cards">
{card("Projetos", str(totals["projects"]))}
{card("Completos", _num(totals["projects_complete"]))}
{card("Testes", _num(totals["tests"]))}
{card("Nichos cobertos", f"{totals['niches_covered']}/{totals['niches_total']}")}
{card("Eventos na cadeia", str(ledger["events"]))}
</div>
{pipeline_block}
<h2>Projetos — medidos por artefato existente</h2>
<table><thead><tr><th>Classe</th><th>Projeto</th><th>Artefatos</th><th>Progresso</th>
<th>Faltando</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<h2>Cobertura por grupo de nicho</h2>
<table><thead><tr><th>Grupo</th><th>Cobertos</th><th>Progresso</th></tr></thead>
<tbody>{"".join(group_rows)}</tbody></table>
{knowledge_block}
<footer>Todo número desta página é derivado de evidência verificável — arquivos que
existem, testes coletados, commits, eventos encadeados. Nenhum status é
autodeclarado. O hash acima é ancorado no ledger.</footer>
</body></html>
"""
