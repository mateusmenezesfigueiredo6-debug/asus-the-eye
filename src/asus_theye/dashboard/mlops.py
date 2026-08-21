# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Painel do dashboard: MLOps — registry, corridas e campeão/desafiante.

Página HTML pura; FastAPI só no registro da rota.  Lê os stores JSONL em
``reports/mlops/{modelos,versoes,corridas,promocoes}.jsonl``; se ausentes,
exibe estado vazio honesto em vez de fingir dado.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .tema import pagina


def _ler_jsonl(caminho: Path) -> list[dict[str, Any]]:
    """Lê um arquivo JSONL e retorna lista de dicts; vazio se ausente ou ilegível."""
    if not caminho.exists():
        return []
    linhas: list[dict[str, Any]] = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            linhas.append(json.loads(linha))
        except json.JSONDecodeError:
            continue
    return linhas


def _metricas_str(metricas: Any) -> str:
    if not isinstance(metricas, dict):
        return html.escape(str(metricas))
    return " ".join(f"{html.escape(str(k))}={html.escape(str(v))}" for k, v in metricas.items())


def _params_str(params: Any) -> str:
    if not isinstance(params, dict):
        return html.escape(str(params))
    return " ".join(f"{html.escape(str(k))}={html.escape(str(v))}" for k, v in params.items())


def _corrida_linha(corrida: dict[str, Any]) -> str:
    modelo = html.escape(str(corrida.get("modelo_id", "—")))
    versao = html.escape(str(corrida.get("versao", "—")))
    spec = _params_str(corrida.get("params", {}))
    metricas = _metricas_str(corrida.get("metricas", {}))
    artefatos = len(corrida.get("artefatos", [])) if isinstance(corrida.get("artefatos"), list) else 0
    _vazio = '<span class="muted">\u2014</span>'
    return (
        f"<tr><td><code>{modelo}@{versao}</code></td>"
        f"<td>{spec or _vazio}</td>"
        f"<td>{metricas or _vazio}</td>"
        f"<td>{artefatos}</td></tr>"
    )


def _campeao_desafiante_secao(
    modelos: list[dict[str, Any]],
    promocoes: list[dict[str, Any]],
    base: Path,
) -> str:
    if not modelos:
        return ""

    from asus_theye.mlops import campeao_atual

    secoes: list[str] = []
    for modelo in modelos:
        mid = str(modelo.get("modelo_id", ""))
        nome = html.escape(str(modelo.get("nome", mid)))
        campea = campeao_atual(mid, base=base)
        camp_html: str
        if campea:
            cv = html.escape(str(campea.get("versao", "—")))
            ca = html.escape(str(campea.get("acoplado_a", "—")))
            camp_html = f'<span class="ok">campeão: {cv}</span> &nbsp;(acoplado a: <code>{ca}</code>)'
        else:
            camp_html = '<span class="muted">sem campeão registrado</span>'

        desafiantes = [p for p in promocoes if str(p.get("modelo_id")) == mid and str(p.get("papel")) == "desafiante"]
        desaf_rows = "".join(
            f"<tr><td><code>{html.escape(str(d.get('versao', '—')))}</code></td>"
            f"<td>{html.escape(str(d.get('promovido_em', '—')))}</td>"
            f"<td>{html.escape(str(d.get('acoplado_a', '—')))}</td></tr>"
            for d in desafiantes
        )
        desaf_tabela = (
            '<div class="table-wrap"><table><thead>'
            "<tr>"
            "<th>versão</th><th>promovido em</th><th>acoplado a</th>"
            "</tr></thead>"
            f"<tbody>{desaf_rows}</tbody></table></div>"
            if desaf_rows
            else '<p class="muted">sem desafiantes registrados</p>'
        )
        secoes.append(
            f'<h3>{nome} <span class="muted">({html.escape(mid)})</span></h3>'
            f"<p>{camp_html}</p>"
            f"<h4>Desafiantes</h4>{desaf_tabela}"
        )

    return "<h2>Campeão / Desafiante por modelo</h2>" + "".join(secoes)


def mlops_page(base: Path | None = None, *, estatico: bool = False) -> str:  # noqa: PLR0914
    """Renderiza o painel MLOps como HTML puro."""
    raiz = Path("reports/mlops") if base is None else base

    modelos = _ler_jsonl(raiz / "modelos.jsonl")
    versoes = _ler_jsonl(raiz / "versoes.jsonl")
    corridas = _ler_jsonl(raiz / "corridas.jsonl")
    promocoes = _ler_jsonl(raiz / "promocoes.jsonl")

    n_modelos = len(modelos)
    n_versoes = len(versoes)
    n_corridas = len(corridas)
    n_promocoes = len(promocoes)

    cards = f"""<section class="cards">
<div class="card"><div class="label">Modelos</div><div class="value">{n_modelos}</div></div>
<div class="card"><div class="label">Versões</div><div class="value">{n_versoes}</div></div>
<div class="card"><div class="label">Corridas</div><div class="value">{n_corridas}</div></div>
<div class="card"><div class="label">Promoções</div><div class="value">{n_promocoes}</div></div>
</section>"""

    if corridas:
        tabela_corridas = (
            "<h2>Corridas</h2>"
            '<div class="table-wrap"><table><thead>'
            "<tr>"
            "<th>modelo@versão</th><th>especificação (params)</th><th>métricas</th><th>artefatos</th>"
            "</tr></thead>"
            f"<tbody>{''.join(_corrida_linha(c) for c in corridas)}</tbody></table></div>"
        )
    else:
        tabela_corridas = '<h2>Corridas</h2><p class="muted">nenhuma corrida registrada</p>'

    try:
        cd_secao = _campeao_desafiante_secao(modelos, promocoes, raiz)
    except Exception:  # noqa: BLE001
        cd_secao = '<p class="muted">campeão/desafiante indisponível</p>'

    aviso = (
        '<p class="muted aviso">&#9888; desafiante não tem peso em nada; '
        "promoção a influência exige a porta declarada na promoção</p>"
    )

    corpo = f"{cards}\n{tabela_corridas}\n{cd_secao}\n{aviso}"
    return pagina(
        titulo="ASUS THE EYE — MLOps",
        corpo="<h1>MLOPS</h1><p class='lede'>corridas de modelo, seladas na corrente</p>" + corpo,
        rota="/mlops",
        estatico=estatico,
    )


def register_mlops_routes(app: Any, base: Path | None = None) -> None:
    """Anexa GET /mlops a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/mlops", response_class=HTMLResponse)
    def get_mlops() -> str:
        return mlops_page(base)
