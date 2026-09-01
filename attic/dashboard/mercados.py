# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Painel dos mercados VIVOS — o coração visível do produto Markets.

A página que o comparador não tem como igualar: cada probabilidade carrega a
PROVENIÊNCIA (bloco ``gerador`` com fontes nomeadas quando nasceu do WPAM;
"prior 0,50" dito como tal quando não), cada liquidação carrega o Brier contra
a fonte oficial, e cada divergência vs comparador viaja com a régua de que
opinião de mercado nunca resolve nada.

Fontes de dados (tudo do repo, nada inventado):
- ``reports/markets/registro.json`` — mercados vivos e liquidados;
- ``reports/markets/comparador.jsonl`` — observações de divergência seladas;
- os 40 retrospectivos NÃO aparecem aqui: são acervo rotulado (ver /evidencia).

Dependency-light como os demais painéis: HTML puro; FastAPI só na rota.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .navegacao import CSS_NAV, barra

BASE_PADRAO = Path("reports/markets")


def _linhas_jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def _badge_probabilidade(mercado: dict[str, Any]) -> str:
    """A probabilidade com a sua proveniência — nunca um número solto."""
    p = float(mercado["probability"])
    gerador = mercado.get("gerador")
    if gerador and gerador.get("fontes"):
        fontes = html.escape("; ".join(str(f) for f in gerador["fontes"]))
        return f'<b>{p:.4f}</b> <span class="ok" title="{fontes}">WPAM</span>'
    return f'<b>{p:.2f}</b> <span class="muted">prior declarado</span>'


def _linha_vivo(mercado: dict[str, Any]) -> str:
    estado = str(mercado["estado"])
    classe = "warn" if estado == "EM_RESOLUCAO" else "ok"
    return (
        f"<tr><td class='id'>{html.escape(str(mercado['claim_id']))}</td>"
        f"<td>{html.escape(str(mercado['question']))}</td>"
        f"<td>{_badge_probabilidade(mercado)}</td>"
        f"<td class='muted'>{html.escape(str(mercado['resolution_source']))}</td>"
        f"<td>{html.escape(str(mercado['deadline']))}</td>"
        f'<td><span class="{classe}">{html.escape(estado)}</span></td></tr>'
    )


def _linha_liquidado(mercado: dict[str, Any]) -> str:
    outcome = int(mercado["outcome"])
    return (
        f"<tr><td class='id'>{html.escape(str(mercado['claim_id']))}</td>"
        f"<td>{'SIM' if outcome == 1 else 'NÃO'}</td>"
        f"<td>{float(mercado['valor_observado']):.2f}</td>"
        f"<td><b>{float(mercado['brier_do_contrato']):.4f}</b></td>"
        f"<td class='muted'>{html.escape(str(mercado['resolution_source']))}</td></tr>"
    )


def _linha_divergencia(obs: dict[str, Any]) -> str:
    return (
        f"<tr><td class='id'>{html.escape(str(obs['claim_id']))}</td>"
        f"<td>{html.escape(str(obs.get('ticker', '—')))}</td>"
        f"<td>{float(obs['our_probability']):.4f}</td>"
        f"<td>{float(obs['comparator_price']):.4f}</td>"
        f"<td><b>{float(obs['divergence']):.4f}</b></td>"
        f"<td class='muted'>{html.escape(str(obs.get('nota_de_mapeamento', ''))[:120])}</td></tr>"
    )


def mercados_page(base: Path | None = None) -> str:
    pasta = base if base is not None else BASE_PADRAO
    registro_path = pasta / "registro.json"
    mercados: list[dict[str, Any]] = []
    if registro_path.exists():
        mercados = json.loads(registro_path.read_text(encoding="utf-8")).get("mercados", [])
    vivos = [m for m in mercados if m.get("estado") in ("ABERTO", "EM_RESOLUCAO")]
    liquidados = [m for m in mercados if m.get("estado") == "LIQUIDADO"]
    divergencias = _linhas_jsonl(pasta / "comparador.jsonl")

    if not mercados:
        corpo = (
            '<section class="cards"><div class="card"><div class="label">Mercados</div>'
            '<div class="value">nenhum</div></div></section>'
            '<p class="muted">Registro vazio. Emita com <code>asus-theye markets-emitir</code> '
            "ou deixe o laço de resolução emitir na próxima liquidação.</p>"
        )
        return _shell(corpo)

    areas = sorted({str(m["market_area_id"]) for m in mercados})
    com_wpam = sum(1 for m in vivos if m.get("gerador"))
    vazio_liq = '<tr><td colspan="5" class="muted">nenhum ainda</td></tr>'
    vazio_div = '<tr><td colspan="6" class="muted">nenhuma observação ainda</td></tr>'
    corpo_liq = "".join(_linha_liquidado(m) for m in liquidados) or vazio_liq
    corpo_div = "".join(_linha_divergencia(o) for o in divergencias) or vazio_div
    corpo = f"""<section class="cards">
<div class="card"><div class="label">Mercados vivos</div><div class="value">{len(vivos)}</div></div>
<div class="card"><div class="label">Liquidados</div><div class="value">{len(liquidados)}</div></div>
<div class="card"><div class="label">Áreas medindo</div><div class="value">{len(areas)}</div></div>
<div class="card"><div class="label">Divergências vs comparador</div><div class="value">{len(divergencias)}</div></div>
</section>
<h2>Mercados vivos — probabilidade com proveniência</h2>
<div class="table-wrap"><table><thead>
<tr><th>claim</th><th>pergunta</th><th>p (origem)</th>
<th>fonte oficial</th><th>prazo</th><th>estado</th></tr></thead>
<tbody>{"".join(_linha_vivo(m) for m in vivos)}</tbody></table></div>
<p class="muted">{com_wpam} de {len(vivos)} vivos nasceram do gerador WPAM (passe o mouse no selo para as fontes);
os demais declaram o prior 0,50 — sem sinal, sem convicção inventada.</p>
<h2>Liquidados — o erro medido contra a fonte oficial</h2>
<div class="table-wrap"><table><thead>
<tr><th>claim</th><th>desfecho</th><th>observado</th>
<th>Brier</th><th>fonte</th></tr></thead>
<tbody>{corpo_liq}</tbody></table></div>
<h2>Divergência vs comparador — medida, nunca resolutora</h2>
<div class="table-wrap"><table><thead>
<tr><th>claim</th><th>ticker</th><th>nossa p</th><th>preço</th>
<th>divergência</th><th>mapeamento</th></tr></thead>
<tbody>{corpo_div}</tbody></table></div>
<p class="muted">Chaox é comparador, nunca fonte de resolução — quem acertou só se sabe depois que o claim
liquidar contra a fonte oficial declarada. Reconstruções retrospectivas do acervo legado NÃO aparecem aqui
(são inelegíveis como previsão; ver a linhagem em /evidencia). Toda liquidação e divergência é evento selado
na cadeia auditável.</p>"""
    return _shell(corpo)


def _shell(corpo: str) -> str:
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE — Mercados</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16;--ok:#4ade80;--bad:#f87171;--warn:#fbbf24}}
*{{box-sizing:border-box}}
body{{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em}}
h2{{margin:28px 0 12px;font-size:1.05rem;letter-spacing:.05em;color:var(--muted);text-transform:uppercase}}
.muted{{color:var(--muted)}}
code{{color:var(--accent)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin-bottom:24px}}
.card{{background:var(--panel);padding:20px;border:1px solid #253149;border-radius:12px}}
.label{{color:var(--muted);font-size:.8rem;text-transform:uppercase}}
.value{{font-size:1.7rem;margin-top:8px;color:var(--accent)}}
.table-wrap{{width:100%;max-width:100%;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;background:var(--panel);
border:1px solid #253149;border-radius:12px;overflow:hidden}}
th,td{{padding:12px 14px;text-align:left;border-bottom:1px solid #253149}}
th{{color:var(--muted);font-size:.78rem;text-transform:uppercase}}
td.id{{font-weight:700;white-space:nowrap}}
.ok{{color:var(--ok)}}.bad{{color:var(--bad)}}.warn{{color:var(--warn)}}
@media (max-width: 640px){{
main{{padding:24px 12px}}
.cards{{grid-template-columns:1fr}}
th,td{{padding:10px 8px}}
th{{font-size:.72rem}}
}}
{CSS_NAV}
</style></head><body><main><h1>MERCADOS — medidos contra a fonte oficial</h1>
{barra("/mercados")}
{corpo}
</main></body></html>"""


def register_mercados_routes(app: Any, base: Path | None = None) -> None:
    """Anexa GET /mercados a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/mercados", response_class=HTMLResponse)
    def get_mercados() -> str:
        return mercados_page(base)
