# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Landing — a porta de entrada dos dois produtos.

O herói desta página não é um número grande com um rótulo pequeno. É **o claim
selado**: a pergunta, a probabilidade que a plataforma publicou, o instante, e o
hash que prova que aquilo foi dito antes do fato. É o artefato mais
característico deste produto, e o único que nenhum concorrente pode exibir
honestamente sem ter a corrente.

Toda a página serve a uma tarefa só: fazer um estranho acreditar que a
probabilidade foi publicada **antes**, e que ele pode conferir sozinho.

Os números vêm da medição selada. Se ela falhar, a página diz que não sabe e
continua navegável — degradar é dizer menos, nunca inventar.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .navegacao import destino
from .tema import estado, hash_fio, leitura, pagina

PRODUTOS: tuple[dict[str, str], ...] = (
    {
        "nome": "Markets",
        "tese": "Perguntas com prazo e critério, respondidas pela fonte oficial — "
        "não por alguém decidindo depois quem ganhou.",
        "detalhe": "Inflação, juros e câmbio, cada um medido contra o Banco Central. A probabilidade "
        "sai antes do fato, com a origem do sinal nomeada. O Brier aparece quando o contrato liquida, "
        "e é <code>null</code> até lá — antes disso não há o que pontuar.",
        "rota": "/mercados",
        "cta": "Ver os mercados",
        "segunda_rota": "/calibracao",
        "segunda": "A probabilidade vale algo?",
    },
    {
        "nome": "Ledger",
        "tese": "A trilha que qualquer pessoa confere sem pedir licença.",
        "detalhe": "Cada passo selado por hash, encadeado ao anterior, e ancorado em blockchain "
        "pública. O verificador responde <strong>sem token</strong>: você não precisa acreditar em "
        "nós — baixe a corrente e refaça a conta. Apagar dado deixa recibo, e a âncora continua "
        "válida.",
        "rota": "/corrente",
        "cta": "Ver a corrente",
        "segunda_rota": "/api",
        "segunda": "Conferir por conta própria",
    },
)


def _heroi(base: Path | None, *, estatico: bool) -> str:
    """O claim selado — a coisa mais característica que esta plataforma tem."""
    from asus_theye.markets.serie_p import SERIE_PADRAO

    registro_path = (base or Path("reports")) / "markets" / "registro.json"
    if not registro_path.exists():
        return '<p class="nota">Registro de mercados indisponível — nenhum claim a exibir.</p>'

    import json

    mercados = json.loads(registro_path.read_text(encoding="utf-8")).get("mercados", [])
    vivos = [m for m in mercados if str(m.get("estado", "ABERTO")).upper() != "LIQUIDADO"]
    if not vivos:
        return '<p class="nota">Nenhum mercado aberto no momento.</p>'

    # o claim que fecha primeiro: o mais próximo de ser respondido pelo mundo
    alvo = min(vivos, key=lambda m: str(m.get("deadline", "9999")))
    p = float(alvo["probability"])
    gerador = alvo.get("gerador") or {}
    fonte = str(gerador.get("metodo") or "prior de máxima incerteza, sem sinal disponível")

    # o hash do último ponto selado deste claim — a prova como ornamento
    fio = ""
    serie = SERIE_PADRAO if base is None else base / "markets" / "serie_p.jsonl"
    if serie.exists():
        pontos = [json.loads(li) for li in serie.read_text(encoding="utf-8").splitlines() if li.strip()]
        do_claim = [pt for pt in pontos if pt.get("claim_id") == alvo["claim_id"]]
        if do_claim:
            fio = hash_fio(str(do_claim[-1].get("ponto_id", "")))

    return f"""<section class="selado" style="margin:2.6rem 0 0">
<div class="rotulo">Publicado antes do fato · {html.escape(str(alvo["claim_id"]))}</div>
<p style="font-size:clamp(1.3rem,3vw,1.75rem);line-height:1.35;margin:.7rem 0 1.2rem;max-width:34ch">
{html.escape(str(alvo["question"]))}</p>
<div style="display:flex;align-items:baseline;gap:1.4rem;flex-wrap:wrap">
<span class="mono v-selo" style="font-size:clamp(3rem,9vw,5rem);font-weight:500;letter-spacing:-.055em;
line-height:.9;font-variant-numeric:tabular-nums">{p * 100:.1f}<span style="font-size:.36em">%</span></span>
<div style="max-width:30ch">
<div class="rotulo">é o que dizemos hoje</div>
<div class="nota" style="margin-top:.35rem">{html.escape(fonte[:180])}</div>
</div></div>
<div style="margin-top:1.2rem;display:flex;gap:.6rem;flex-wrap:wrap;align-items:center">
{estado("aberto", "latao")}
<span class="mono" style="color:var(--tinta-3)">fecha em {html.escape(str(alvo["deadline"]))}</span>
<span class="mono" style="color:var(--tinta-3)">·</span>
<span class="mono" style="color:var(--tinta-3)">resolve contra {html.escape(str(alvo["resolution_source"]))}</span>
</div>
{fio}
</section>"""


def _leituras(base: Path | None) -> str:
    """Os números vivos da corrente. Falha vira aviso, nunca zero falso."""
    from asus_theye.projeto import MedicaoError, medir_projeto

    try:
        snap = medir_projeto(base) if base is not None else medir_projeto()
    except MedicaoError as erro:
        return f'<p class="nota">Medição indisponível — a navegação continua válida.<br>{html.escape(str(erro))}</p>'

    corrente, capacidade = snap["corrente"], snap["capacidade_real"]
    medicao, ancoragem = snap["medicao_continua"], snap["ancoragem"]
    integra = corrente["verifica"]
    return (
        '<div class="leituras">'
        + leitura(
            "Corrente", corrente["eventos"], "íntegra" if integra else "QUEBRADA", "v-selo" if integra else "v-oxido"
        )
        + leitura("Âncoras", ancoragem["ancoras"], "Base Sepolia (rede de teste)", "v-selo")
        + leitura(
            "Mercados vivos", medicao["mercados"] - medicao["liquidados"], f"{medicao['liquidados']} liquidado(s)"
        )
        + leitura("Atividade", capacidade["eventos_prospectivos"], "eventos prospectivos")
        + "</div>"
    )


def _produto(p: dict[str, str], *, estatico: bool) -> str:
    return f"""<article style="padding:2.2rem 0;border-top:1px solid var(--regua)">
<div class="rotulo">THE EYE</div>
<h3 style="font-size:clamp(1.45rem,3.4vw,2rem);letter-spacing:-.02em;margin:.3rem 0 .9rem">
{html.escape(p["nome"])}</h3>
<p style="font-size:1.1rem;line-height:1.5;margin:0 0 .8rem;max-width:48ch">{html.escape(p["tese"])}</p>
<p class="nota" style="margin:0 0 1.3rem">{p["detalhe"]}</p>
<div style="display:flex;gap:1.6rem;flex-wrap:wrap;align-items:center">
<a href="{html.escape(destino(p["rota"], estatico=estatico))}"
style="font-family:var(--grotesca);font-weight:600;font-size:.94rem;text-decoration:none;
color:var(--selo);border-bottom:1.5px solid var(--selo);padding-bottom:2px">{html.escape(p["cta"])}</a>
<a href="{html.escape(destino(p["segunda_rota"], estatico=estatico))}"
style="font-family:var(--grotesca);font-size:.88rem;text-decoration:none;color:var(--tinta-3)">
{html.escape(p["segunda"])}</a>
</div></article>"""


def landing_page(base: Path | None = None, *, estatico: bool = False) -> str:
    """Página inicial. Degrada dizendo o que falta, nunca inventando."""
    produtos = "".join(_produto(p, estatico=estatico) for p in PRODUTOS)
    corpo = f"""<h1>A probabilidade sai antes do fato — e fica provado que saiu.</h1>
<p class="lede">Perguntas com prazo e critério, respondidas pela fonte oficial. Cada passo selado
numa corrente que qualquer pessoa verifica, sem pedir acesso a ninguém.</p>
{_heroi(base, estatico=estatico)}
{_leituras(base)}
<h2>Dois produtos</h2>
{produtos}
<div class="ressalva">
<span class="rotulo">O que esta plataforma recusa fazer</span>
Comparador nunca resolve — preço de mercado alheio é opinião agregada, não desfecho.
Sem sinal, dizemos <code>p = 0,50</code> e declaramos que não sabemos, em vez de fabricar
confiança. E nenhum número aparece sem o método que o produziu ao lado.
</div>"""
    return pagina(titulo="ASUS THE EYE — mercados preditivos auditáveis", corpo=corpo, rota="/", estatico=estatico)


def register_landing_routes(app: Any, base: Path | None = None) -> None:
    """Anexa GET / a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/", response_class=HTMLResponse)
    def get_landing() -> str:
        return landing_page(base)
