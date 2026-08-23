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

from .tema import pagina


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
    marcas = "".join(f'<circle cx="{px(p):.1f}" cy="{py(o):.1f}" r="4" fill="var(--selo)"/>' for p, o in pontos)
    linha = ""
    if len(pontos) > 1:
        caminho = " ".join(f"{px(p):.1f},{py(o):.1f}" for p, o in sorted(pontos))
        linha = f'<polyline points="{caminho}" fill="none" stroke="var(--selo)" stroke-width="2"/>'
    vazio = (
        ""
        if pontos
        else f'<text x="{lado / 2}" y="{lado / 2}" fill="var(--tinta-3)" font-size="11" text-anchor="middle">'
        "sem faixa com amostra suficiente</text>"
    )
    return f"""<svg viewBox="0 0 {lado} {lado}" width="100%" style="max-width:340px" role="img"
aria-label="curva de confiabilidade contra a diagonal">
<rect x="{margem}" y="{margem}" width="{util}" height="{util}" fill="var(--papel-2)" stroke="var(--regua)"/>
<line x1="{px(0)}" y1="{py(0)}" x2="{px(1)}" y2="{py(1)}" stroke="var(--tinta-3)" stroke-width="1.5"
stroke-dasharray="5,4"/>
{linha}{marcas}{vazio}
<text x="{lado / 2}" y="{lado - 6}" fill="var(--tinta-3)" font-size="10"
text-anchor="middle">probabilidade declarada</text>
<text x="11" y="{lado / 2}" fill="var(--tinta-3)" font-size="10" text-anchor="middle"
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


def _bloco_trilhas(snap: dict[str, Any]) -> str:
    """As duas probabilidades, lado a lado — a seção que responde à pergunta.

    A pergunta que nenhuma medição anterior desta plataforma respondia é: *o
    número publicado sabe algo que o consenso não sabe?* Enquanto a
    probabilidade derivava do boletim Focus, a resposta era estruturalmente
    "não dá para saber". Esta seção existe para que a resposta passe a ser o
    que os dados disserem — inclusive, e provavelmente, que a trilha própria
    perde. Perder medindo vale mais que a posição de antes, que era não medir.
    """
    comp = snap.get("trilhas") or {}
    if not comp:
        return ""

    def _linha(li: dict[str, Any]) -> str:
        # helper em vez de f-string aninhada: o projeto roda em 3.10, onde
        # reusar a aspa externa dentro da expressão é erro de sintaxe
        marca = " <span class='muted'>(benchmark)</span>" if li["trilha"] == comp.get("benchmark") else ""
        return (
            f"<tr><td>{html.escape(str(li['trilha']))}{marca}</td>"
            f"<td>{li['n']}</td><td>{_num(li.get('brier'))}</td></tr>"
        )

    linhas = "".join(_linha(li) for li in comp.get("por_trilha", []))
    skill = comp.get("skill_score")
    valor = "—" if skill is None else f"{float(skill):+.4f}"

    return f"""<h2>As duas trilhas</h2>
<p class="muted">Cada mercado publica <b>duas</b> probabilidades, ambas seladas antes do desfecho:
a do <b>consenso Focus</b> e a da <b>cobertura noticiosa</b>, que não passa pelo consenso em ponto
algum. Na liquidação as duas são pontuadas com a mesma régua.</p>
<section class="cards">
<div class="card"><div class="label">Desfechos casados</div><div class="value">{comp.get("claims_casados", 0)}</div>
<div class="muted">mínimo para comparar: {comp.get("claims_minimos", "—")}</div></div>
<div class="card"><div class="label">Pares casados</div><div class="value">{comp.get("n_casados", 0)}</div>
<div class="muted">um por dia — cem pares de três contratos são três desfechos</div></div>
<div class="card"><div class="label">Skill score da trilha própria</div><div class="value">{valor}</div>
<div class="muted">contra o Focus como benchmark declarado</div></div>
</section>
<div class="table-wrap"><table><thead><tr><th>trilha</th><th>n</th><th>Brier</th></tr></thead>
<tbody>{linhas}</tbody></table></div>
<div class="ressalva">{html.escape(str(comp.get("leitura", "")))}</div>
<p class="muted">{html.escape(str(comp.get("metodo", "")))}</p>"""


def _corpo_insuficiente(snap: dict[str, Any]) -> str:
    """O que o painel mostra quando ainda não há o que mostrar — e por quê."""
    exc = snap["excluidos"]
    motivos = "".join(
        f"<tr><td>{html.escape(nome.replace('_', ' '))}</td><td>{qtd}</td></tr>" for nome, qtd in exc.items()
    )
    return f"""<section class="cards">
<div class="card"><div class="label">Desfechos distintos</div><div class="value">{snap.get("claims", 0)}</div>
<div class="muted">mínimo para agregar: {snap.get("claims_minimos", "—")}</div></div>
<div class="card"><div class="label">Pares utilizáveis</div><div class="value">{snap["n"]}</div>
<div class="muted">um por dia de série — não são observações independentes</div></div>
<div class="card"><div class="label">Brier</div><div class="value">—</div>
<div class="muted">não calculado</div></div>
</section>
<div class="ressalva"><b>Amostra insuficiente — nada foi agregado.</b><br>
{html.escape(str(snap["metodo"]))}</div>
<h2>Por que sobrou tão pouco</h2>
<div class="table-wrap"><table><thead><tr><th>ponto excluído porque…</th><th>quantos</th></tr></thead>
<tbody>{motivos}</tbody></table></div>
{_bloco_trilhas(snap)}
<h2>O que precisa acontecer</h2>
<ol class="passos">
<li>Um claim com <b>série de p(t)</b> precisa <b>liquidar</b> — hoje os pontos são de mercados vivos.</li>
<li>A liquidação precisa registrar <b>determination_date</b> com base confiável (o cron já faz).</li>
<li>Repetir até <b>{snap.get("claims_minimos", "—")}</b> contratos <b>distintos</b> liquidarem.
Não adianta acumular dias: a série grava um ponto por dia, mas trinta pontos de um contrato
continuam sendo <b>um</b> desfecho. Não há atalho — calibração é sobre contratos que terminam.</li>
</ol>
<p class="muted">{html.escape(str(snap["metodo_do_horizonte"]))}</p>"""


def _corpo_medido(snap: dict[str, Any]) -> str:
    murphy = snap["murphy"] or {}
    faixas = "".join(
        f"<tr><td>{html.escape(str(f['faixa']))}</td><td>{f['n']}</td><td>{f.get('claims', '—')}</td>"
        f"<td>{_num(f['p_media_declarada'], 3)}</td>"
        f"<td>{_num(f['frequencia_observada'], 3)}</td></tr>"
        for f in snap["curva"]
    )
    return f"""<section class="cards">
<div class="card"><div class="label">Desfechos distintos</div><div class="value">{snap.get("claims", 0)}</div>
<div class="muted">o tamanho amostral que vale</div></div>
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
<tr><th>faixa de p</th><th>n</th><th>desfechos</th><th>p média declarada</th><th>frequência observada</th></tr></thead>
<tbody>{faixas}</tbody></table></div>
{_bloco_trilhas(snap)}
{_tabela("Brier por horizonte (re-ancorado)", snap["por_horizonte"], "faixa")}
{_tabela("Brier por área", snap["por_area"], "area")}
<p class="muted">{html.escape(str(murphy.get("nota", "")))} ·
taxa-base observada: {murphy.get("taxa_base", "—")}</p>
<p class="muted">{html.escape(str(snap["metodo_do_horizonte"]))}</p>"""


def calibracao_page(
    *,
    serie: Path | None = None,
    resolucoes: Path | None = None,
    estatico: bool = False,
) -> str:
    """Página da calibração. Degrada dizendo o que falta, nunca desenhando ruído."""
    from asus_theye.markets.calibracao import RESOLUCOES_PADRAO, SERIE_PADRAO, CalibracaoError, medir

    try:
        snap = medir(serie=serie or SERIE_PADRAO, resolucoes=resolucoes or RESOLUCOES_PADRAO)
    except CalibracaoError as error:
        return pagina(
            titulo="ASUS THE EYE — Calibração",
            rota="/calibracao",
            estatico=estatico,
            corpo=(f'<div class="rotulo">Calibração</div><p class="nota">indisponível — {html.escape(str(error))}</p>'),
        )
    return pagina(
        titulo="ASUS THE EYE — Calibração",
        rota="/calibracao",
        estatico=estatico,
        corpo="<h1>CALIBRAÇÃO</h1><p class='lede'>a probabilidade declarada vale alguma coisa?</p>"
        + (_corpo_medido(snap) if snap["suficiente"] else _corpo_insuficiente(snap)),
    )


def register_calibracao_routes(app: Any) -> None:
    """Anexa GET /calibracao a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/calibracao", response_class=HTMLResponse)
    def get_calibracao() -> str:
        return calibracao_page()
