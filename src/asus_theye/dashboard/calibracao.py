# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Painel de calibração — a probabilidade declarada vale alguma coisa?

É a peça que mais diferencia esta plataforma: publicações de referência trazem
estudos de calibração **agregados e estáticos**; aqui a medição é **viva, por
contrato e selada na corrente**, e qualquer pessoa refaz a conta a partir dos
mesmos arquivos.

Diferença de postura que o painel encarna: **quando não há amostra, ele diz
isso e explica o que falta**, em vez de desenhar uma curva bonita sobre ruído.
Gráfico convence mais do que merece — desenhar cedo demais seria a forma mais
eficiente de destruir a credibilidade que a corrente existe para construir.

A curva é SVG inline, sem dependência externa e sem script: o painel precisa
funcionar como arquivo estático publicado, e uma biblioteca de gráfico traria
runtime de terceiro para dentro da vitrine.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .navegacao import CSS_NAV, barra


def _svg_confiabilidade(curva: list[dict[str, Any]]) -> str:
    """Curva de confiabilidade contra a diagonal — SVG puro, sem dependência.

    A diagonal é o previsor perfeitamente calibrado. Faixa sem amostra
    suficiente simplesmente não vira ponto: buraco honesto é melhor do que
    ponto inventado.
    """
    lado, margem = 320, 34
    util = lado - 2 * margem

    def px(valor: float) -> float:
        return margem + valor * util

    def py(valor: float) -> float:
        return lado - margem - valor * util

    pontos = [
        (float(f["p_media_declarada"]), float(f["frequencia_observada"]))
        for f in curva
        if f.get("suficiente") and f.get("p_media_declarada") is not None and f.get("frequencia_observada") is not None
    ]
    marcas = "".join(f'<circle cx="{px(p):.1f}" cy="{py(o):.1f}" r="4" fill="#67e8f9"/>' for p, o in pontos)
    linha = ""
    if len(pontos) > 1:
        caminho = " ".join(f"{px(p):.1f},{py(o):.1f}" for p, o in sorted(pontos))
        linha = f'<polyline points="{caminho}" fill="none" stroke="#67e8f9" stroke-width="2"/>'
    vazio = (
        ""
        if pontos
        else f'<text x="{lado / 2}" y="{lado / 2}" fill="#9aa8bd" font-size="11" text-anchor="middle">'
        "sem faixa com amostra suficiente</text>"
    )
    return f"""<svg viewBox="0 0 {lado} {lado}" width="100%" style="max-width:340px" role="img"
aria-label="curva de confiabilidade contra a diagonal">
<rect x="{margem}" y="{margem}" width="{util}" height="{util}" fill="#101725" stroke="#253149"/>
<line x1="{px(0)}" y1="{py(0)}" x2="{px(1)}" y2="{py(1)}" stroke="#4b5563" stroke-width="1.5"
stroke-dasharray="5,4"/>
{linha}{marcas}{vazio}
<text x="{lado / 2}" y="{lado - 6}" fill="#9aa8bd" font-size="10" text-anchor="middle">probabilidade declarada</text>
<text x="11" y="{lado / 2}" fill="#9aa8bd" font-size="10" text-anchor="middle"
transform="rotate(-90 11 {lado / 2})">frequência observada</text>
</svg>"""


def _num(valor: Any, casas: int = 4) -> str:
    """Número formatado, ou travessão quando ausente. Nunca imprime 'None'."""
    return "—" if valor is None else f"{float(valor):.{casas}f}"


def _tabela(titulo: str, linhas: list[dict[str, Any]], chave: str) -> str:
    corpo = "".join(
        f"<tr><td>{html.escape(str(li[chave]))}</td><td>{li['n']}</td><td>{_num(li.get('brier'))}</td></tr>"
        for li in linhas
    )
    return (
        f"<h2>{html.escape(titulo)}</h2><div class='table-wrap'><table><thead>"
        f"<tr><th>{html.escape(chave)}</th><th>n</th><th>Brier</th></tr></thead>"
        f"<tbody>{corpo}</tbody></table></div>"
    )


def _corpo_insuficiente(snap: dict[str, Any]) -> str:
    """O que o painel mostra quando ainda não há o que mostrar — e por quê."""
    exc = snap["excluidos"]
    motivos = "".join(
        f"<tr><td>{html.escape(nome.replace('_', ' '))}</td><td>{qtd}</td></tr>" for nome, qtd in exc.items()
    )
    return f"""<section class="cards">
<div class="card"><div class="label">Pares utilizáveis</div><div class="value">{snap["n"]}</div>
<div class="muted">mínimo para agregar: {snap["amostra_minima"]}</div></div>
<div class="card"><div class="label">Brier</div><div class="value">—</div>
<div class="muted">não calculado</div></div>
</section>
<div class="ressalva"><b>Amostra insuficiente — nada foi agregado.</b><br>
{html.escape(str(snap["metodo"]))}</div>
<h2>Por que sobrou tão pouco</h2>
<div class="table-wrap"><table><thead><tr><th>ponto excluído porque…</th><th>quantos</th></tr></thead>
<tbody>{motivos}</tbody></table></div>
<h2>O que precisa acontecer</h2>
<ol class="passos">
<li>Um claim com <b>série de p(t)</b> precisa <b>liquidar</b> — hoje os pontos são de mercados vivos.</li>
<li>A liquidação precisa registrar <b>determination_date</b> com base confiável (o cron já faz).</li>
<li>Repetir até <b>{snap["amostra_minima"]}</b> pares. Não há atalho: calibração é sobre acúmulo.</li>
</ol>
<p class="muted">{html.escape(str(snap["metodo_do_horizonte"]))}</p>"""


def _corpo_medido(snap: dict[str, Any]) -> str:
    murphy = snap["murphy"] or {}
    faixas = "".join(
        f"<tr><td>{html.escape(str(f['faixa']))}</td><td>{f['n']}</td>"
        f"<td>{_num(f['p_media_declarada'], 3)}</td>"
        f"<td>{_num(f['frequencia_observada'], 3)}</td></tr>"
        for f in snap["curva"]
    )
    return f"""<section class="cards">
<div class="card"><div class="label">Pares</div><div class="value">{snap["n"]}</div></div>
<div class="card"><div class="label">Brier</div><div class="value">{_num(snap["brier"])}</div>
<div class="muted">menor é melhor</div></div>
<div class="card"><div class="label">Confiabilidade</div>
<div class="value">{murphy.get("confiabilidade", "—")}</div><div class="muted">menor é melhor</div></div>
<div class="card"><div class="label">Resolução</div>
<div class="value">{murphy.get("resolucao", "—")}</div><div class="muted">maior é melhor</div></div>
</section>
<h2>Curva de confiabilidade</h2>
<p class="muted">A tracejada é o previsor perfeitamente calibrado. Faixa sem amostra suficiente
não vira ponto — buraco honesto é melhor que ponto inventado.</p>
{_svg_confiabilidade(snap["curva"])}
<div class="table-wrap"><table><thead>
<tr><th>faixa de p</th><th>n</th><th>p média declarada</th><th>frequência observada</th></tr></thead>
<tbody>{faixas}</tbody></table></div>
{_tabela("Brier por horizonte (re-ancorado)", snap["por_horizonte"], "faixa")}
{_tabela("Brier por área", snap["por_area"], "area")}
<p class="muted">{html.escape(str(murphy.get("nota", "")))} ·
taxa-base observada: {murphy.get("taxa_base", "—")}</p>
<p class="muted">{html.escape(str(snap["metodo_do_horizonte"]))}</p>"""


def calibracao_page(
    *,
    serie: Path | None = None,
    resolucoes: Path | None = None,
) -> str:
    """Página da calibração. Degrada dizendo o que falta, nunca desenhando ruído."""
    from asus_theye.markets.calibracao import RESOLUCOES_PADRAO, SERIE_PADRAO, CalibracaoError, medir

    try:
        snap = medir(serie=serie or SERIE_PADRAO, resolucoes=resolucoes or RESOLUCOES_PADRAO)
    except CalibracaoError as error:
        return _shell(
            '<section class="cards"><div class="card"><div class="label">Calibração</div>'
            f'<div class="value">indisponível</div></div></section><p class="muted">{html.escape(str(error))}</p>'
        )
    return _shell(_corpo_medido(snap) if snap["suficiente"] else _corpo_insuficiente(snap))


def _shell(corpo: str) -> str:
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE — Calibração</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16;--ok:#4ade80;--bad:#f87171}}
*{{box-sizing:border-box}}
body{{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em;margin:0 0 6px}}
h2{{margin:28px 0 12px;font-size:1.05rem;letter-spacing:.05em;color:var(--muted);text-transform:uppercase}}
.muted{{color:var(--muted)}}
code{{color:var(--accent);word-break:break-all}}
a{{color:var(--accent)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:20px}}
.card{{background:var(--panel);padding:20px;border:1px solid #253149;border-radius:12px}}
.label{{color:var(--muted);font-size:.8rem;text-transform:uppercase}}
.value{{font-size:1.7rem;margin:8px 0 4px;color:var(--accent)}}
.ressalva{{background:#1b2436;border-left:3px solid var(--accent);padding:14px 16px;border-radius:8px;
margin:16px 0;line-height:1.5}}
.passos{{line-height:1.7;max-width:80ch}}
.table-wrap{{width:100%;max-width:100%;overflow-x:auto;margin-top:12px}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid #253149;border-radius:12px}}
th,td{{padding:12px 14px;text-align:left;border-bottom:1px solid #253149}}
th{{color:var(--muted);font-size:.78rem;text-transform:uppercase}}
{CSS_NAV}
@media (max-width:640px){{main{{padding:24px 12px}}.cards{{grid-template-columns:1fr}}th,td{{padding:10px 8px}}}}
</style></head><body><main>
<h1>CALIBRAÇÃO</h1>
<p class="muted">a probabilidade declarada vale alguma coisa?</p>
{barra("/calibracao")}
{corpo}
</main></body></html>"""


def register_calibracao_routes(app: Any) -> None:
    """Anexa GET /calibracao a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/calibracao", response_class=HTMLResponse)
    def get_calibracao() -> str:
        return calibracao_page()
