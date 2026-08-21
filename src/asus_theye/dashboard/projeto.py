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

from .tema import pagina

ESTADO_ROTULO = {"concluida": ("ok", "concluída"), "parcial": ("warn", "parcial"), "pendente": ("bad", "pendente")}


def _fase_linha(fase: dict[str, Any]) -> str:
    classe, rotulo = ESTADO_ROTULO.get(str(fase.get("estado")), ("bad", str(fase.get("estado"))))
    pct = f"{float(fase['peso_concluido']) * 100:.0f}%"
    return (
        f"<tr><td>{html.escape(str(fase['id']))}</td><td>{html.escape(str(fase['nome']))}</td>"
        f'<td><span class="{classe}">{rotulo}</span></td><td>{pct}</td>'
        f'<td class="muted">{html.escape(str(fase["metodo"]))}</td></tr>'
    )


def projeto_page(base: Path | None = None, *, estatico: bool = False) -> str:
    from asus_theye.projeto import MedicaoError, medir_projeto

    try:
        snap = medir_projeto(base) if base is not None else medir_projeto()
    except MedicaoError as error:
        corpo = (
            '<section class="cards"><div class="card"><div class="label">Medição</div>'
            '<div class="value">indisponível</div></div></section>'
            f'<p class="muted">{html.escape(str(error))}</p>'
        )
        return pagina(
            titulo="ASUS THE EYE — Projeto",
            corpo="<h1>MEDIÇÃO DO PROJETO</h1><p class='lede'>cada número com o método ao lado</p>" + corpo,
            rota="/projeto",
            estatico=estatico,
        )

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
<div class="table-wrap"><table><thead>
<tr><th>fase</th><th>nome</th><th>estado</th><th>%</th><th>método</th></tr></thead>
<tbody>
{"".join(_fase_linha(f) for f in caminho["fases"])}
</tbody></table></div>
{_tabela_produtos(produtos)}
<p class="muted">{html.escape(str(snap["ressalva"]))} Selagem: <code>asus-theye projeto-medir</code> —
mesmo estado não re-sela (dedupe); estado novo vira evento novo na cadeia.</p>"""
    return pagina(
        titulo="ASUS THE EYE — Projeto",
        corpo="<h1>MEDIÇÃO DO PROJETO</h1><p class='lede'>cada número com o método ao lado</p>" + corpo,
        rota="/projeto",
        estatico=estatico,
    )


def _tabela_produtos(produtos: dict[str, Any]) -> str:
    """O checklist vivo do roteiro até os 2 produtos — some com honestidade se não declarado."""
    if not produtos["fases"]:
        return f'<p class="muted">{html.escape(str(produtos["metodo"]))}</p>'
    return (
        "<h2>Roteiro dos produtos (checklist vivo)</h2>"
        '<div class="table-wrap"><table><thead>'
        "<tr><th>fase</th><th>nome</th><th>estado</th><th>%</th><th>método</th></tr></thead>"
        f"<tbody>{''.join(_fase_linha(f) for f in produtos['fases'])}</tbody></table></div>"
    )


def register_projeto_routes(app: Any, base: Path | None = None) -> None:
    """Anexa GET /projeto a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/projeto", response_class=HTMLResponse)
    def get_projeto() -> str:
        return projeto_page(base)
