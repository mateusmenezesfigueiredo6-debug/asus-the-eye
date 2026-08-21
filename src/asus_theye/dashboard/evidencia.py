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

from .tema import pagina


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


def evidencia_page(base: str | Path | None = None, *, estatico: bool = False) -> str:
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
        return pagina(
            titulo="ASUS THE EYE — Evidência",
            corpo="<h1>EVIDÊNCIA</h1><p class='lede'>a linhagem de cada número até a fonte</p>" + corpo,
            rota="/evidencia",
            estatico=estatico,
        )

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
    return pagina(
        titulo="ASUS THE EYE — Evidência",
        corpo="<h1>EVIDÊNCIA</h1><p class='lede'>a linhagem de cada número até a fonte</p>"
        + cards
        + blocos_html
        + aviso,
        rota="/evidencia",
        estatico=estatico,
    )


def register_evidencia_routes(app: Any, base: str | Path | None = None) -> None:
    """Anexa GET /evidencia a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/evidencia", response_class=HTMLResponse)
    def get_evidencia() -> str:
        return evidencia_page(base)
