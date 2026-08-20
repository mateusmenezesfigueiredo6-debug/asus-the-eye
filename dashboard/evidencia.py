# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Painel da Evidência — ontologia e linhagem verificável, no navegador.

Torna visual o que `asus_theye.evidence` computa: os objetos da plataforma
(Fonte → Mercado → Resolução → EventoSelado → LoteMerkle → Âncora) e a
linhagem de cada evento selado até a Fonte primária. Dependency-light como
`markets.py` — a página é uma string HTML pura; FastAPI só entra na rota.

Sem corrente (nenhum evento selado ainda), degrada para um estado vazio honesto.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from asus_theye.evidence.entidades import EVENTO, FONTE

from .navegacao import CSS_NAV, barra


def _cor_do_tipo(tipo: str) -> str:
    return {
        "Fonte": "var(--ok)",
        "Mercado": "var(--accent)",
        "Resolucao": "var(--accent)",
        "EventoSelado": "var(--ink)",
        "LoteMerkle": "var(--warn)",
        "Ancora": "var(--warn)",
        "Comparador": "var(--bad)",
    }.get(tipo, "var(--muted)")


def evidencia_page(base: str | Path | None = None) -> str:
    from asus_theye.evidence import construir_grafo, linhagem_ascendente
    from asus_theye.evidence.grafo import BASE_PADRAO

    grafo = construir_grafo(Path(base) if base is not None else BASE_PADRAO)
    if not grafo.nos:
        corpo = (
            '<section class="cards"><div class="card"><div class="label">Corrente</div>'
            '<div class="value">vazia</div></div></section>'
            '<p class="muted">Nenhum evento selado ainda. Rode <code>asus-theye markets-resolve</code> '
            "para medir e selar; a linhagem aparece aqui.</p>"
        )
        return _shell(corpo)

    tipos = [chave[0] for chave in grafo.nos]
    tem_ancora = any(t == "Ancora" for t in tipos)
    no_recibo = next((n for n in grafo.nos.values() if n.tipo == "Recibo"), None)
    if no_recibo is None:
        recibo_html = "—"
    else:
        estado_recibo = str(no_recibo.dados.get("estado"))
        classe_recibo = (
            "ok" if estado_recibo == "valid" else ("bad" if estado_recibo in ("tampered", "invalid") else "warn")
        )
        recibo_html = f'<span class="{classe_recibo}">{estado_recibo}</span>'
    cards = f"""<section class="cards">
<div class="card"><div class="label">Objetos</div><div class="value">{len(grafo.nos)}</div></div>
<div class="card"><div class="label">Relações</div><div class="value">{len(grafo.arestas)}</div></div>
<div class="card"><div class="label">Eventos selados</div><div class="value">{tipos.count("EventoSelado")}</div></div>
<div class="card"><div class="label">Artefatos de fonte</div><div class="value">{tipos.count("Artefato")}</div></div>
<div class="card"><div class="label">Recibo do verificador</div><div class="value">{recibo_html}</div></div>
<div class="card"><div class="label">Ancorado on-chain</div>
<div class="value">{'<span class="ok">sim</span>' if tem_ancora else '<span class="warn">ainda não</span>'}</div></div>
</section>"""

    # Linhagem de cada evento selado até a Fonte — a pergunta da categoria Palantir.
    blocos = ["<h2>Linhagem verificável (evento → Fonte primária)</h2>"]
    eventos = sorted(
        (n for n in grafo.nos.values() if n.tipo == EVENTO),
        key=lambda n: int(n.dados.get("sequence", 0)),
    )
    if not eventos:
        blocos.append('<p class="muted">Ainda sem evento selado na corrente.</p>')
    for ev in eventos:
        cadeia = [ev, *linhagem_ascendente(grafo, ev.tipo, ev.id)]
        setas = []
        for no in cadeia:
            rotulo = html.escape(f"{no.tipo}: {no.rotulo}")
            setas.append(f'<span class="no" style="border-color:{_cor_do_tipo(no.tipo)}">{rotulo}</span>')
        chega = any(no.tipo == FONTE for no in cadeia)
        selo = '<span class="ok">→ Fonte provada</span>' if chega else '<span class="warn">→ parcial</span>'
        hashv = html.escape(str(ev.dados.get("event_hash_sha256", ""))[:24])
        blocos.append(
            f'<div class="linha"><div class="cadeia">{" ".join(setas)}</div>'
            f'<div class="meta">hash {hashv}… &nbsp; {selo}</div></div>'
        )

    aviso = (
        ""
        if tem_ancora
        else (
            '<p class="muted">A âncora on-chain ainda não existe: a linhagem é honestamente '
            "PARCIAL (para no evento selado). Ancore para estendê-la até a raiz Merkle pública.</p>"
        )
    )
    blocos_html = "\n".join(blocos)
    return _shell(cards + blocos_html + aviso)


def _shell(corpo: str) -> str:
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE — Evidência</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16;--ok:#4ade80;--bad:#f87171;--warn:#f59e0b}}
*{{box-sizing:border-box}}
body{{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em}} h2{{margin-top:28px;font-size:1.1rem}}
.muted{{color:var(--muted)}} code{{color:var(--accent)}}
.ok{{color:var(--ok)}}.bad{{color:var(--bad)}}.warn{{color:var(--warn)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin-bottom:8px}}
.card{{background:var(--panel);padding:20px;border:1px solid #253149;border-radius:12px}}
.label{{color:var(--muted);font-size:.8rem;text-transform:uppercase}}
.value{{font-size:1.7rem;margin-top:8px;color:var(--accent)}}
.table-wrap{{width:100%;max-width:100%;overflow-x:auto}}
.linha{{background:var(--panel);border:1px solid #253149;border-radius:12px;padding:14px;margin:10px 0}}
.cadeia{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
.no{{border:1px solid;border-radius:8px;padding:4px 10px;font-size:.85rem}}
.meta{{color:var(--muted);font-size:.78rem;margin-top:8px;font-family:monospace}}
@media (max-width: 640px){{
main{{padding:24px 12px}}
.cards{{grid-template-columns:1fr}}
.label{{font-size:.74rem}}
.meta{{font-size:.72rem}}
}}
{CSS_NAV}
</style></head><body><main><h1>EVIDÊNCIA — linhagem verificável</h1>
{barra("/evidencia")}
{corpo}
</main></body></html>"""


def register_evidencia_routes(app: Any, base: str | Path | None = None) -> None:
    """Anexa GET /evidencia a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/evidencia", response_class=HTMLResponse)
    def get_evidencia() -> str:
        return evidencia_page(base)
