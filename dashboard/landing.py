# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Landing — a rota ``/``, que até aqui devolvia 404.

Quem abria a raiz do servidor via ``{"detail":"Not Found"}``: os oito painéis
existiam mas nenhum caminho levava até eles. Esta página é a porta de entrada —
diz o que a plataforma é, mostra os dois produtos e leva a cada painel.

Os números vêm da MESMA medição selada na cadeia (``asus-theye projeto-medir``),
nunca de valores escritos à mão aqui. Se a medição não estiver disponível, a
página diz isso e continua servindo a navegação: degradar é dizer menos, nunca
inventar.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .navegacao import CSS_NAV, barra

PRODUTOS: tuple[dict[str, str], ...] = (
    {
        "nome": "THE EYE Markets",
        "resumo": "Mercados preditivos que se resolvem sozinhos contra a fonte oficial — "
        "IPCA, Selic e câmbio, cada um medido pelo BCB, não por opinião.",
        "prova": "Cada emissão, resolução e liquidação vira evento selado. O Brier é "
        "publicado quando o contrato liquida — e é <code>null</code> até lá.",
        "rota": "/mercados",
    },
    {
        "nome": "THE EYE Ledger",
        "resumo": "A trilha de auditoria que qualquer pessoa confere sem pedir licença: "
        "corrente encadeada por hash, ancorada em blockchain pública.",
        "prova": "Verificador público responde sem token. A âncora prova QUANDO a "
        "corrente existia; o encadeamento prova que ela não mudou depois.",
        "rota": "/corrente",
    },
)

DOUTRINA: tuple[str, ...] = (
    "Comparador nunca resolve. Kalshi e afins entram como <em>divergência medida</em>, jamais como fonte de verdade.",
    "Sem sinal, <code>p = 0,50</code> declarado — a plataforma prefere dizer "
    "&ldquo;não sei&rdquo; a fabricar confiança que não tem.",
    "Nenhum número sem método: todo percentual carrega, ao lado, de onde saiu.",
)


def _cartoes_de_prova(base: Path | None) -> str:
    """Os números vivos da corrente. Falha de medição vira aviso, não zero falso."""
    from asus_theye.projeto import MedicaoError, medir_projeto

    try:
        snap = medir_projeto(base) if base is not None else medir_projeto()
    except MedicaoError as error:
        return (
            '<p class="muted">Medição indisponível — a navegação acima continua válida.<br>'
            f"{html.escape(str(error))}</p>"
        )

    corrente, capacidade = snap["corrente"], snap["capacidade_real"]
    ancoragem, medicao = snap["ancoragem"], snap["medicao_continua"]
    verifica = '<span class="ok">íntegra</span>' if corrente["verifica"] else '<span class="bad">QUEBRADA</span>'
    return f"""<section class="cards">
<div class="card"><div class="label">Corrente auditável</div>
<div class="value">{corrente["eventos"]}</div><div class="muted">eventos — {verifica}</div></div>
<div class="card"><div class="label">Âncoras on-chain</div>
<div class="value">{ancoragem["ancoras"]}</div><div class="muted">Base Sepolia</div></div>
<div class="card"><div class="label">Mercados vivos</div>
<div class="value">{medicao["mercados"] - medicao["liquidados"]}</div>
<div class="muted">{medicao["liquidados"]} já liquidado(s)</div></div>
<div class="card"><div class="label">Atividade prospectiva</div>
<div class="value">{capacidade["eventos_prospectivos"]}</div>
<div class="muted">exclui import retrospectivo</div></div>
</section>
<p class="muted">Medição selada na cadeia: <code>{snap["hash_da_medicao"][:32]}…</code> ·
caminho mínimo {snap["caminho_minimo"]["pct"]}% · <a href="/projeto">placar completo</a></p>"""


def _cartao_produto(produto: dict[str, str]) -> str:
    return (
        f'<article class="produto"><h3>{html.escape(produto["nome"])}</h3>'
        f"<p>{html.escape(produto['resumo'])}</p>"
        f'<p class="muted">{produto["prova"]}</p>'
        f'<p><a class="cta" href="{html.escape(produto["rota"])}">ver o painel →</a></p></article>'
    )


def landing_page(base: Path | None = None) -> str:
    """Página inicial: o que é, os dois produtos, os números vivos e para onde ir."""
    produtos = "".join(_cartao_produto(p) for p in PRODUTOS)
    doutrina = "".join(f"<li>{item}</li>" for item in DOUTRINA)
    corpo = f"""<p class="lede">Mercados preditivos <strong>auditáveis</strong>: a probabilidade é
publicada antes do fato, a resolução vem da fonte oficial, e cada passo fica selado numa
corrente que qualquer pessoa verifica — sem pedir acesso a ninguém.</p>
{_cartoes_de_prova(base)}
<h2>Os dois produtos</h2>
<section class="produtos">{produtos}</section>
<h2>A doutrina, em três linhas</h2>
<ul class="doutrina">{doutrina}</ul>
<p class="muted">Verificação independente: <code>GET /health</code>, <code>GET /verify</code> e
<code>GET /root/:data</code> no verificador público respondem <strong>sem token</strong>.
Ver <a href="/api">a API</a>.</p>"""
    return _shell(corpo)


def _shell(corpo: str) -> str:
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE — mercados preditivos auditáveis</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16;--ok:#4ade80;--bad:#f87171}}
*{{box-sizing:border-box}}
body{{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em;margin:0 0 6px}}
h2{{margin:34px 0 12px;font-size:1.05rem;letter-spacing:.05em;color:var(--muted);text-transform:uppercase}}
h3{{margin:0 0 10px;color:var(--accent);font-size:1.15rem}}
.lede{{font-size:1.12rem;line-height:1.6;max-width:70ch;margin:0 0 28px}}
.muted{{color:var(--muted)}}
code{{color:var(--accent);word-break:break-all}}
a{{color:var(--accent)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin-bottom:20px}}
.card{{background:var(--panel);padding:20px;border:1px solid #253149;border-radius:12px}}
.label{{color:var(--muted);font-size:.8rem;text-transform:uppercase}}
.value{{font-size:1.7rem;margin:8px 0 4px;color:var(--accent)}}
.produtos{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.produto{{background:var(--panel);padding:24px;border:1px solid #253149;border-radius:12px}}
.produto p{{line-height:1.55}}
.cta{{text-decoration:none;font-weight:600}}
.doutrina{{max-width:80ch;line-height:1.6;padding-left:20px}}
.doutrina li{{margin:8px 0}}
.ok{{color:var(--ok)}}.bad{{color:var(--bad)}}
{CSS_NAV}
@media (max-width:640px){{main{{padding:24px 12px}}.cards,.produtos{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>ASUS THE EYE</h1>
<p class="muted">mercados preditivos auditáveis</p>
{barra("/")}
{corpo}
</main></body></html>"""


def register_landing_routes(app: Any, base: Path | None = None) -> None:
    """Anexa GET / a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/", response_class=HTMLResponse)
    def get_landing() -> str:
        return landing_page(base)
