# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Painel do dashboard: a medição do projeto — quanto falta, com hash.

O dash que o dono pediu: o placar inteiro do projeto, cada número com o método
ao lado, e o hash canônico da medição em destaque (a mesma medição que a CLI
``projeto-medir`` sela na cadeia auditável). Dependency-light como os demais
painéis: página HTML pura; FastAPI só no registro da rota.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

ESTADO_ROTULO = {"concluida": ("ok", "concluída"), "parcial": ("warn", "parcial"), "pendente": ("bad", "pendente")}


def _fase_linha(fase: dict[str, Any]) -> str:
    classe, rotulo = ESTADO_ROTULO.get(str(fase.get("estado")), ("bad", str(fase.get("estado"))))
    pct = f"{float(fase['peso_concluido']) * 100:.0f}%"
    return (
        f"<tr><td>{html.escape(str(fase['id']))}</td><td>{html.escape(str(fase['nome']))}</td>"
        f'<td><span class="{classe}">{rotulo}</span></td><td>{pct}</td>'
        f'<td class="muted">{html.escape(str(fase["metodo"]))}</td></tr>'
    )


def projeto_page(base: Path | None = None) -> str:
    from asus_theye.projeto import MedicaoError, medir_projeto

    try:
        snap = medir_projeto(base) if base is not None else medir_projeto()
    except MedicaoError as error:
        corpo = (
            '<section class="cards"><div class="card"><div class="label">Medição</div>'
            '<div class="value">indisponível</div></div></section>'
            f'<p class="muted">{html.escape(str(error))}</p>'
        )
        return _shell(corpo)

    caminho = snap["caminho_minimo"]
    produtos = snap["produtos"]
    corrente = snap["corrente"]
    medicao = snap["medicao_continua"]
    ancoragem = snap["ancoragem"]
    verifica = '<span class="ok">✓</span>' if corrente["verifica"] else '<span class="bad">✗</span>'
    topo = (corrente["topo_hash"] or "—")[:16]
    pct_produtos = "—" if produtos["pct"] is None else f"{produtos['pct']}%"
    corpo = f"""<section class="cards">
<div class="card"><div class="label">Caminho mínimo</div><div class="value">{caminho["pct"]}%</div></div>
<div class="card"><div class="label">Roteiro dos produtos</div><div class="value">{pct_produtos}</div></div>
<div class="card"><div class="label">Corrente (eventos)</div>
<div class="value">{corrente["eventos"]} {verifica}</div></div>
<div class="card"><div class="label">Liquidados / resoluções</div>
<div class="value">{medicao["liquidados"]} / {medicao["resolucoes"]}</div></div>
<div class="card"><div class="label">Âncoras on-chain</div><div class="value">{ancoragem["ancoras"]}</div></div>
<div class="card"><div class="label">Corridas ML</div>
<div class="value">{snap["mlops"]["corridas"]}</div></div>
</section>
<p class="muted">hash da medição: <code>{snap["hash_da_medicao"]}</code> · topo da corrente: <code>{topo}…</code></p>
<h2>Caminho mínimo (F0–F5)</h2>
<table><thead><tr><th>fase</th><th>nome</th><th>estado</th><th>%</th><th>método</th></tr></thead>
<tbody>
{"".join(_fase_linha(f) for f in caminho["fases"])}
</tbody></table>
{_tabela_produtos(produtos)}
<p class="muted">{html.escape(str(snap["ressalva"]))} Selagem: <code>asus-theye projeto-medir</code> —
mesmo estado não re-sela (dedupe); estado novo vira evento novo na cadeia.</p>"""
    return _shell(corpo)


def _tabela_produtos(produtos: dict[str, Any]) -> str:
    """O checklist vivo do roteiro até os 2 produtos — some com honestidade se não declarado."""
    if not produtos["fases"]:
        return f'<p class="muted">{html.escape(str(produtos["metodo"]))}</p>'
    return (
        "<h2>Roteiro dos produtos (checklist vivo)</h2>"
        "<table><thead><tr><th>fase</th><th>nome</th><th>estado</th><th>%</th><th>método</th></tr></thead>"
        f"<tbody>{''.join(_fase_linha(f) for f in produtos['fases'])}</tbody></table>"
    )


def _shell(corpo: str) -> str:
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE — Projeto</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16;--ok:#4ade80;--bad:#f87171;--warn:#fbbf24}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em}}
h2{{margin:28px 0 12px;font-size:1.05rem;letter-spacing:.05em;color:var(--muted);text-transform:uppercase}}
.muted{{color:var(--muted)}}
code{{color:var(--accent);word-break:break-all}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin-bottom:24px}}
.card{{background:var(--panel);padding:20px;border:1px solid #253149;border-radius:12px}}
.label{{color:var(--muted);font-size:.8rem;text-transform:uppercase}}
.value{{font-size:1.7rem;margin-top:8px;color:var(--accent)}}
table{{width:100%;border-collapse:collapse;background:var(--panel);
border:1px solid #253149;border-radius:12px;overflow:hidden}}
th,td{{padding:12px 14px;text-align:left;border-bottom:1px solid #253149}}
th{{color:var(--muted);font-size:.78rem;text-transform:uppercase}}
.ok{{color:var(--ok)}}.bad{{color:var(--bad)}}.warn{{color:var(--warn)}}
</style></head><body><main><h1>MEDIÇÃO DO PROJETO</h1>
{corpo}
</main></body></html>"""


def register_projeto_routes(app: Any, base: Path | None = None) -> None:
    """Anexa GET /projeto a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/projeto", response_class=HTMLResponse)
    def get_projeto() -> str:
        return projeto_page(base)
