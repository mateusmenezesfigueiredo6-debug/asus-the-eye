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

PRODUTOS: tuple[dict[str, Any], ...] = (
    {
        "nome": "Markets",
        "lente": "probabilidade selada antes do fato",
        "tese": "Perguntas com prazo e critério, respondidas pela fonte oficial — "
        "não por alguém decidindo depois quem ganhou.",
        "detalhe": "Inflação, juros e câmbio, cada um medido contra o Banco Central. A probabilidade "
        "sai antes do fato, com a origem do sinal nomeada. O Brier aparece quando o contrato liquida, "
        "e é <code>null</code> até lá — antes disso não há o que pontuar.",
        # cada linha aqui vira uma <li> abaixo do detalhe. Fatos concretos, não promessas.
        "provas": (
            "Fonte oficial: Banco Central (SGS)",
            "Duas trilhas por mercado: consenso Focus e cobertura noticiosa",
            "Sem dinheiro real — Lei 14.790/2023",
        ),
        "rota": "/mercados",
        "cta": "Ver os mercados",
        "segunda_rota": "/calibracao",
        "segunda": "A probabilidade vale algo?",
    },
    {
        "nome": "Ledger",
        "lente": "a prova que qualquer um confere",
        "tese": "A trilha que qualquer pessoa confere sem pedir licença.",
        "detalhe": "Cada passo selado por hash, encadeado ao anterior, e ancorado em blockchain "
        "pública. O verificador responde <strong>sem token</strong>: você não precisa acreditar em "
        "nós — baixe a corrente e refaça a conta. Apagar dado deixa recibo, e a âncora continua "
        "válida.",
        "provas": (
            "Corrente por hash encadeado, verificável offline",
            "Âncoras on-chain na Base Sepolia",
            "Expurgo com recibo: LGPD sem quebrar a prova",
        ),
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


def _produto(p: dict[str, Any], *, estatico: bool) -> str:
    """Um cartão de produto no grid da vitrine — dois produtos, peso igual.

    Estrutura fixa (importa para paridade): rótulo curto → nome grande → lente
    em uma linha → tese em serifa → detalhe em nota → provas em <ul> → dois CTAs.
    Se um produto ganhar mais linhas de prova, o outro ganha também; a paridade
    é do desenho, não do texto.
    """
    provas = "".join(f"<li>{html.escape(x)}</li>" for x in p["provas"])
    return f"""<article class="card" style="padding:1.6rem 1.7rem;gap:.6rem">
<div class="label">THE EYE · {html.escape(p["lente"])}</div>
<h3 style="font-family:var(--grotesca);font-weight:700;letter-spacing:-.02em;
font-size:clamp(1.6rem,3.4vw,2.1rem);margin:.1rem 0 .3rem">{html.escape(p["nome"])}</h3>
<p style="font-family:var(--serifa);font-size:1.08rem;line-height:1.45;margin:0 0 .5rem">{html.escape(p["tese"])}</p>
<p class="muted" style="margin:0 0 .8rem;font-size:.86rem;line-height:1.5">{p["detalhe"]}</p>
<ul style="padding-left:1.05rem;margin:0 0 1rem;font-size:.82rem;color:var(--tinta-2);line-height:1.5">
{provas}
</ul>
<div style="display:flex;gap:1.4rem;flex-wrap:wrap;align-items:center;margin-top:auto">
<a href="{html.escape(destino(p["rota"], estatico=estatico))}"
style="font-family:var(--grotesca);font-weight:600;font-size:.94rem;text-decoration:none;
color:var(--selo);border-bottom:1.5px solid var(--selo);padding-bottom:2px">{html.escape(p["cta"])}</a>
<a href="{html.escape(destino(p["segunda_rota"], estatico=estatico))}"
style="font-family:var(--grotesca);font-size:.86rem;text-decoration:none;color:var(--tinta-3)">
{html.escape(p["segunda"])}</a>
</div></article>"""


def _vitrine_dois(base: Path | None, *, estatico: bool) -> str:
    """Os dois produtos, lado a lado, com peso IGUAL.

    A ordem visual (Markets à esquerda, Ledger à direita) é convenção; o que
    importa é a paridade — mesmo card, mesmo peso tipográfico, mesma quantidade
    de âncoras factuais debaixo do CTA. Antes, o hero era só do Markets e o
    Ledger caía no meio de um parágrafo; a queixa "cadê a Palantir? só estou
    vendo a Chaox" era descritiva da tela, não do produto.
    """
    grade = "grid-template-columns:repeat(auto-fit,minmax(320px,1fr));margin-top:2.4rem"
    return f"""<section class="cards" style="{grade}">
{"".join(_produto(p, estatico=estatico) for p in PRODUTOS)}
</section>"""


#: Os seis passos da disciplina que os DOIS produtos compartilham. Cada um traz
#: a GUARDA — o que aquele passo impede — porque é a guarda, não a função, que
#: distingue esta plataforma de qualquer painel bonito com números.
_PASSOS_DISCIPLINA: tuple[tuple[str, str], ...] = (
    ("Pergunta com prazo", "Critério numérico escrito ANTES. Depois não se altera."),
    ("Fonte oficial nomeada", "Só órgão público. Comparador nunca resolve."),
    ("Bruto arquivado", "sha256 do arquivo original, no instante da leitura."),
    ("Probabilidade selada", "Sem sinal, p = 0,50 declarado — nunca confiança fabricada."),
    ("Desfecho pela fonte", "Quem decide é quem apura. Nunca a aritmética da casa."),
    ("Brier + elo ancorado", "Cada elo cita o anterior. Reescrever o passado quebra todos."),
)


def _diagrama_disciplina() -> str:
    """A disciplina compartilhada, desenhada — SVG puro, sem dependência.

    POR QUE DESENHAR. A tese desta plataforma ("a probabilidade saiu antes do
    fato, e você pode conferir") é uma afirmação sobre PROCESSO, e processo em
    prosa some. Desenhado, vira uma cadeia onde dá para apontar o passo em que
    o compromisso é selado e o passo que torna a reescrita detectável.

    POR QUE A GUARDA E NÃO A FUNÇÃO. Qualquer painel exibe "fonte oficial". O
    que separa este é a recusa embutida em cada passo — e é a recusa que
    interessa a quem audita.

    Sem números aqui, de propósito: os números vivos já aparecem logo abaixo,
    lidos da medição selada. Diagrama com número decorado envelhece calado.
    """
    largura, caixa_h, topo, margem, vao = 960, 84, 30, 10, 14
    n = len(_PASSOS_DISCIPLINA)
    caixa_w = (largura - margem * 2 - vao * (n - 1)) / n
    altura = topo + caixa_h + 104

    partes: list[str] = [
        f'<svg viewBox="0 0 {largura} {altura:.0f}" width="100%" role="img" '
        f'aria-label="A disciplina compartilhada pelos dois produtos, em seis passos: '
        f'pergunta com prazo e critério declarado antes, fonte oficial nomeada, bruto '
        f'arquivado com sha256, probabilidade selada, desfecho decidido pela fonte, e '
        f'Brier medido com elo ancorado em corrente encadeada.">',
        f'<text x="{margem}" y="14" font-size="12" fill="currentColor" fill-opacity="0.55">'
        f'A mesma disciplina nos dois produtos — e a guarda de cada passo</text>',
    ]
    for i, (titulo, guarda) in enumerate(_PASSOS_DISCIPLINA):
        x = margem + i * (caixa_w + vao)
        meio = x + caixa_w / 2
        partes.append(
            f'<rect x="{x:.1f}" y="{topo}" width="{caixa_w:.1f}" height="{caixa_h}" rx="7" '
            f'fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.22"/>'
            f'<text x="{x + 10:.1f}" y="{topo + 18}" font-size="10" fill="currentColor" '
            f'fill-opacity="0.45">{i + 1}</text>'
        )
        # título em até duas linhas, quebrando no espaço mais central
        palavras = titulo.split()
        corte = len(palavras) // 2 or 1
        linhas = [" ".join(palavras[:corte]), " ".join(palavras[corte:])] if len(palavras) > 2 else [titulo]
        for j, linha in enumerate(l for l in linhas if l):
            partes.append(
                f'<text x="{meio:.1f}" y="{topo + 44 + j * 16}" font-size="13" '
                f'fill="currentColor" text-anchor="middle">{html.escape(linha)}</text>'
            )
        if i < n - 1:
            partes.append(
                f'<path d="M {x + caixa_w + 2:.1f} {topo + caixa_h / 2:.0f} l {vao - 5} 0 '
                f'm -5 -4 l 5 4 l -5 4" stroke="currentColor" stroke-opacity="0.4" fill="none"/>'
            )
        partes.append(
            f'<foreignObject x="{x:.1f}" y="{topo + caixa_h + 8}" width="{caixa_w:.1f}" height="90">'
            f'<div xmlns="http://www.w3.org/1999/xhtml" style="font:11px/1.35 system-ui,sans-serif;'
            f'color:currentColor;opacity:.6;text-align:center;padding:0 3px">'
            f'{html.escape(guarda)}</div></foreignObject>'
        )
    partes.append("</svg>")
    return (
        '<section style="margin:2rem 0">'
        '<h2>Como funciona, em seis passos</h2>'
        '<div style="overflow-x:auto">' + "".join(partes) + "</div>"
        "</section>"
    )


def landing_page(base: Path | None = None, *, estatico: bool = False) -> str:
    """Página inicial. Degrada dizendo o que falta, nunca inventando.

    A ordem visual: tese > vitrine dos DOIS produtos com peso igual > números
    vivos > amostra concreta (o claim mais próximo de responder) > a recusa
    que assina a doutrina. O hero-de-um-produto-só saiu — a tese fica antes
    e cobre os dois.
    """
    corpo = f"""<h1>A probabilidade sai antes do fato — e fica provado que saiu.</h1>
<p class="lede">Perguntas com prazo e critério, respondidas pela fonte oficial. Cada passo selado
numa corrente que qualquer pessoa verifica, sem pedir acesso a ninguém. <b>Dois produtos</b>,
mesma disciplina.</p>
{_vitrine_dois(base, estatico=estatico)}
{_diagrama_disciplina()}
{_leituras(base)}
<h2>Um exemplo concreto — o claim mais próximo de responder</h2>
{_heroi(base, estatico=estatico)}
<div class="ressalva" style="margin-top:2.2rem">
<span class="rotulo">O que esta plataforma recusa fazer</span>
Comparador nunca resolve — preço de mercado alheio é opinião agregada, não desfecho.
Sem sinal, dizemos <code>p = 0,50</code> e declaramos que não sabemos, em vez de fabricar
confiança. E nenhum número aparece sem o método que o produziu ao lado.
</div>"""
    return pagina(
        titulo="ASUS THE EYE — mercados preditivos auditáveis",
        corpo=corpo,
        rota="/",
        estatico=estatico,
        descricao=(
            "Dois produtos: THE EYE Markets (probabilidade selada antes do fato) e THE EYE Ledger "
            "(prova que qualquer um confere). Resolvidos contra fonte oficial, ancorados on-chain."
        ),
    )


def register_landing_routes(app: Any, base: Path | None = None) -> None:
    """Anexa GET / a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/", response_class=HTMLResponse)
    def get_landing() -> str:
        return landing_page(base)
