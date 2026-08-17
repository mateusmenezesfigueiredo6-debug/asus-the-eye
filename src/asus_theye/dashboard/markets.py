"""Painel do dashboard: reconciliação e skill dos mercados preditivos.

Torna visual o que a CLI ``markets-reconcile`` reporta: o tie-out contra o banco
medido (o ``scoring`` do módulo reproduz o ``brier_do_contrato`` gravado) e a
skill por área contra um palpite constante. Dependency-light como
``benchmark.py`` — a página é uma string HTML pura, sem exigir FastAPI para ser
construída ou testada; FastAPI só entra no registro da rota.

Quando o banco não está disponível (``ASUS_MARKETS_DB`` não definido), a página
degrada para um estado vazio honesto em vez de estourar.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

_HISTORICO_VOTO = 0.959126  # taxa histórica de seguimento partidário (comparação de vitrine)


def _gather(db_path: str | Path | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    from asus_theye.markets import MarketsSourceError, reconcile, skill_report

    try:
        reconciliation = reconcile(db_path)
        skill = skill_report(db_path)
        return reconciliation, skill, None
    except MarketsSourceError as error:
        return None, None, str(error)


def _fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6f}"
    return html.escape(str(value))


def _rows(reconciliation: dict[str, Any], skill: dict[str, Any]) -> str:
    skill_by_area = {area["area_id"]: area for area in skill["areas"]}
    rows: list[str] = []
    for area in reconciliation["areas"]:
        area_id = html.escape(str(area["area_id"]))
        bate = area["aggregate_matches"] and area["per_contract_matches"]
        badge = '<span class="ok">tie-out</span>' if bate else '<span class="bad">DIVERGE</span>'
        sk = skill_by_area.get(area["area_id"], {})
        skill_value = sk.get("skill_score")
        skill_txt = "indefinida" if skill_value is None else f"{skill_value:+.4f}"
        skill_badge = (
            '<span class="bad">baseline vence</span>'
            if sk.get("baseline_beats_model")
            else '<span class="ok">tem skill</span>'
        )
        rows.append(
            f"<tr><td>{area_id}</td><td>{area['n']}</td>"
            f"<td>{_fmt(area['module_brier'])}</td><td>{_fmt(area['published_brier'])}</td>"
            f"<td>{badge}</td><td>{skill_txt}</td><td>{skill_badge}</td></tr>"
        )
    return "\n".join(rows)


def markets_page(db_path: str | Path | None = None) -> str:
    reconciliation, skill, error = _gather(db_path)

    if error is not None or reconciliation is None or skill is None:
        detalhe = html.escape(error or "banco não disponível")
        corpo = (
            '<section class="cards"><div class="card"><div class="label">Banco</div>'
            f'<div class="value">indisponível</div></div></section>'
            f'<p class="muted">{detalhe}</p>'
            '<p class="muted">Defina <code>ASUS_MARKETS_DB</code> apontando para o asus_teste.duckdb '
            "e recarregue.</p>"
        )
        return _shell(corpo)

    tie_out = reconciliation["tie_out"]
    tie_badge = '<span class="ok">True</span>' if tie_out else '<span class="bad">False</span>'
    com_skill = sum(1 for area in skill["areas"] if not area.get("baseline_beats_model"))
    corpo = f"""<section class="cards">
<div class="card"><div class="label">Liquidados</div><div class="value">{reconciliation["settled_total"]}</div></div>
<div class="card"><div class="label">Tie-out</div><div class="value">{tie_badge}</div></div>
<div class="card"><div class="label">Áreas medidas</div><div class="value">{len(reconciliation["areas"])}</div></div>
<div class="card"><div class="label">Com skill (baseline in-sample)</div><div class="value">{com_skill}</div></div>
</section>
<table><thead><tr>
<th>área</th><th>n</th><th>Brier módulo</th><th>Brier publicado</th><th>reconciliação</th>
<th>skill</th><th>veredito</th>
</tr></thead><tbody>
{_rows(reconciliation, skill)}
</tbody></table>
<p class="muted">Skill contra a taxa-base de cada área (palpite constante in-sample). Áreas de desfecho
constante dão baseline perfeito e skill indefinida — o limiar de máxima incerteza. Para a comparação
de vitrine do voto contra a taxa histórica ({_HISTORICO_VOTO}), use
<code>asus-theye markets-reconcile --skill --baseline {_HISTORICO_VOTO}</code>.</p>"""
    return _shell(corpo)


def _shell(corpo: str) -> str:
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE — Mercados</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16;--ok:#4ade80;--bad:#f87171}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em}}
.muted{{color:var(--muted)}}
code{{color:var(--accent)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin-bottom:24px}}
.card{{background:var(--panel);padding:20px;border:1px solid #253149;border-radius:12px}}
.label{{color:var(--muted);font-size:.8rem;text-transform:uppercase}}
.value{{font-size:1.7rem;margin-top:8px;color:var(--accent)}}
table{{width:100%;border-collapse:collapse;background:var(--panel);
border:1px solid #253149;border-radius:12px;overflow:hidden}}
th,td{{padding:12px 14px;text-align:left;border-bottom:1px solid #253149}}
th{{color:var(--muted);font-size:.78rem;text-transform:uppercase}}
.ok{{color:var(--ok)}}.bad{{color:var(--bad)}}
</style></head><body><main><h1>MERCADOS PREDITIVOS</h1>
{corpo}
</main></body></html>"""


def register_markets_routes(app: Any, db_path: str | Path | None = None) -> None:
    """Anexa GET /markets a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/markets", response_class=HTMLResponse)
    def get_markets() -> str:
        return markets_page(db_path)
