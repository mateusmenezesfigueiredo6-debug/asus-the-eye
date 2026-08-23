# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""O tema — um sistema de design, no lugar de CSS copiado em dez arquivos.

Antes daqui cada painel carregava a própria cópia das mesmas regras. Dez
cópias divergem: uma ganha um ajuste, outra não, e em pouco tempo o produto
parece dez produtos. Aqui o tema é um só.

**A direção, e por que esta.** Isto não é um painel de métricas — é um
instrumento de registro. O artefato mais característico deste produto é o
*claim selado*: uma pergunta, uma probabilidade, um instante e um hash que
prova que aquilo foi dito **antes** do fato. A página tem uma única tarefa —
fazer um estranho acreditar nisso sem ter que pedir permissão a ninguém.

Daí as escolhas:

- **Papel, não console.** O fundo é papel de arquivo, não preto de terminal.
  Um registro que pretende durar se parece com um documento, não com um
  monitor. O modo escuro existe e é tinta sobre papel invertido, não neon.

- **Verdigris para o que está selado.** O verde de bronze oxidado é a cor da
  pátina — do que foi registrado e ficou. Usada **só** em estado selado e
  verificado, nunca como enfeite. Latão para o que está aberto e ainda pode
  mudar; óxido para o que quebrou, e quase nunca aparece.

- **Serifa para afirmação, grotesca para instrumento.** É o inverso do
  costume, e de propósito: as *afirmações* (o que a plataforma diz sobre o
  mundo) são texto de registro; os *rótulos e números* são leitura de
  aparelho. A hierarquia carrega a diferença entre alegar e medir.

- **Sem chamar fonte de terceiro.** Uma página cujo argumento é "você não
  precisa confiar em ninguém" não deveria telefonar para o Google para
  renderizar. A personalidade vem do tratamento — escala, entrelinha,
  contraste de peso, caixa — não de fonte exótica.

**A assinatura:** o hash como ornamento. Todo objeto selado mostra o próprio
hash correndo como um fio de monoespaçada na borda — legível para quem se
aproxima, textura para quem passa. A prova é a decoração. Nenhum concorrente
pode usar isso honestamente, porque nenhum tem a prova.
"""

from __future__ import annotations

import html
from typing import Any

# ---------------------------------------------------------------- paleta

TOKENS = """
:root{
  /* papel de arquivo — levemente quente, e distante do creme de catálogo */
  --papel:#FBFAF7; --papel-2:#F4F2EC; --regua:#DAD6CD;
  --tinta:#14161A; --tinta-2:#4A4E57; --tinta-3:#7C818B;
  /* verdigris: a pátina do que foi registrado e ficou. SÓ para selado. */
  --selo:#1F5C4A; --selo-clara:#E7F0EB;
  /* latão envelhecido: aberto, ainda pode mudar */
  --latao:#8A6D2F; --latao-clara:#F5EEDF;
  /* óxido: quebrado. Deve aparecer quase nunca. */
  --oxido:#8C2F1F;
  --sombra:0 1px 2px rgba(20,22,26,.04), 0 8px 24px -12px rgba(20,22,26,.10);
  /* aliases semânticos usados pelos módulos das páginas
     (evidencia._cor_do_tipo, benchmark, e páginas que ainda escrevem style="color:var(--ok)").
     Os nomes canônicos são --selo/--latao/--oxido — estes aqui apontam para eles, para que
     nada nas páginas fique com border-color vazio quando o tema é o único CSS carregado. */
  --ok: var(--selo);
  --warn: var(--latao);
  --bad: var(--oxido);
  --accent: var(--selo);
  --ink: var(--tinta);
  --muted: var(--tinta-3);
  --serifa:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --grotesca:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,"SF Mono","Cascadia Mono","Roboto Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-tema="claro"]){
    --papel:#111317; --papel-2:#181B20; --regua:#2A2E35;
    --tinta:#ECEAE4; --tinta-2:#A8ADB6; --tinta-3:#767C86;
    --selo:#5FC49E; --selo-clara:#16241F;
    --latao:#D6AC5C; --latao-clara:#241E12;
    --oxido:#E0715C;
    --sombra:0 1px 2px rgba(0,0,0,.3), 0 8px 24px -12px rgba(0,0,0,.5);
  }
}
"""

BASE = """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--papel);color:var(--tinta);
  font:400 17px/1.6 var(--serifa);overflow-x:hidden;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
main{max-width:74rem;margin:0 auto;padding:clamp(2rem,5vw,4.5rem) clamp(1.25rem,4vw,3rem) 5rem}
a{color:inherit}
::selection{background:var(--selo);color:var(--papel)}
:focus-visible{outline:2px solid var(--selo);outline-offset:3px;border-radius:2px}

/* --- cabeçalho: a marca como instrumento, não como logotipo --- */
.topo{display:flex;align-items:baseline;gap:.9rem;flex-wrap:wrap;
  padding-bottom:1.4rem;border-bottom:1px solid var(--regua);margin-bottom:.6rem}
.marca{font-family:var(--grotesca);font-weight:700;font-size:.95rem;
  letter-spacing:.24em;text-transform:uppercase;color:var(--tinta)}
.marca em{font-style:normal;color:var(--tinta-3)}
.local{font-family:var(--mono);font-size:.72rem;color:var(--tinta-3);
  letter-spacing:.06em;margin-left:auto}

/* --- tipografia --- */
h1{font-family:var(--grotesca);font-weight:700;letter-spacing:-.025em;
  font-size:clamp(2.1rem,5.4vw,3.6rem);line-height:1.04;margin:2.4rem 0 0;
  max-width:19ch}
h2{font-family:var(--grotesca);font-weight:650;letter-spacing:-.01em;
  font-size:clamp(1.15rem,2.4vw,1.5rem);line-height:1.2;margin:3.4rem 0 1rem}
h3{font-family:var(--grotesca);font-weight:650;font-size:1.02rem;
  letter-spacing:-.005em;margin:0 0 .5rem}
.lede{font-size:clamp(1.08rem,2vw,1.28rem);line-height:1.55;color:var(--tinta-2);
  max-width:56ch;margin:1.1rem 0 0}
p{max-width:64ch}
.rotulo{font-family:var(--grotesca);font-size:.66rem;font-weight:650;
  letter-spacing:.16em;text-transform:uppercase;color:var(--tinta-3)}
.nota{font-size:.86rem;line-height:1.55;color:var(--tinta-2);max-width:62ch}
.mono{font-family:var(--mono);font-size:.78rem;letter-spacing:-.01em}

/* --- a assinatura: o hash como ornamento --- */
.selado{position:relative;padding-bottom:1.6rem}
.hash-fio{display:block;font-family:var(--mono);font-size:.58rem;
  letter-spacing:.02em;color:var(--tinta-3);opacity:.55;overflow:hidden;
  white-space:nowrap;text-overflow:clip;margin-top:1rem;
  border-top:1px solid var(--regua);padding-top:.5rem;user-select:all}
.hash-fio::before{content:"selado ";font-family:var(--grotesca);
  font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;color:var(--selo)}

/* --- leitura de instrumento --- */
.leituras{display:grid;gap:1px;background:var(--regua);border:1px solid var(--regua);
  grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));margin:2rem 0}
.leitura{background:var(--papel);padding:1.15rem 1.25rem}
.leitura .valor{font-family:var(--mono);font-weight:500;
  font-size:clamp(1.5rem,3.4vw,2rem);letter-spacing:-.04em;
  line-height:1;margin:.5rem 0 .35rem;font-variant-numeric:tabular-nums}
.leitura .glosa{font-size:.78rem;color:var(--tinta-3);line-height:1.4}
.v-selo{color:var(--selo)} .v-latao{color:var(--latao)} .v-oxido{color:var(--oxido)}

/* --- estados --- */
.marca-estado{display:inline-flex;align-items:center;gap:.4rem;
  font-family:var(--grotesca);font-size:.66rem;font-weight:650;
  letter-spacing:.1em;text-transform:uppercase;padding:.24rem .6rem;
  border-radius:2px;white-space:nowrap}
.e-selo{background:var(--selo-clara);color:var(--selo)}
.e-latao{background:var(--latao-clara);color:var(--latao)}
.e-oxido{background:var(--oxido);color:var(--papel)}

/* --- tabelas: registro, não planilha --- */
.rolagem,.table-wrap{overflow-x:auto;margin:1.4rem 0;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:.88rem}
thead th{font-family:var(--grotesca);font-size:.64rem;font-weight:650;
  letter-spacing:.14em;text-transform:uppercase;color:var(--tinta-3);
  text-align:left;padding:0 1rem .6rem 0;border-bottom:1px solid var(--tinta)}
tbody td{padding:.85rem 1rem .85rem 0;border-bottom:1px solid var(--regua);
  vertical-align:baseline}
tbody tr:last-child td{border-bottom:none}
td.num{font-family:var(--mono);font-variant-numeric:tabular-nums;
  letter-spacing:-.02em;white-space:nowrap}

/* --- a ressalva: onde a plataforma diz o que NÃO sabe --- */
.ressalva{border-left:2px solid var(--selo);padding:.2rem 0 .2rem 1.4rem;
  margin:2rem 0;max-width:64ch}
.ressalva .rotulo{color:var(--selo);display:block;margin-bottom:.4rem}

/* --- navegação --- */
nav.the-eye{display:flex;flex-wrap:wrap;gap:.15rem .3rem;margin:1.2rem 0 0}
nav.the-eye a{font-family:var(--grotesca);font-size:.8rem;font-weight:550;
  color:var(--tinta-3);text-decoration:none;padding:.45rem .7rem;
  border-radius:2px;transition:color .15s,background .15s}
nav.the-eye a:hover{color:var(--tinta);background:var(--papel-2)}
nav.the-eye a[aria-current="page"]{color:var(--tinta);background:var(--papel-2);
  box-shadow:inset 0 -2px 0 var(--selo)}

/* --- rodapé --- */
footer.the-eye{margin:5rem 0 0;padding-top:1.6rem;border-top:1px solid var(--regua);
  font-size:.8rem;line-height:1.6;color:var(--tinta-3);max-width:70ch}
footer.the-eye strong{color:var(--tinta-2);font-weight:600}


/* ================================================================
   Classes que as páginas usam há tempo, agora com estilo de verdade.
   Sem elas o produto lia como "só caixa"; com elas cada uma cumpre a
   semântica que a exploração da FASE B nomeou (card = leitura/painel,
   ok/warn/bad = estado). Nada aqui inventa cor — só mapeia para os
   tokens já declarados acima.
   ================================================================ */

/* .cards = grelha de painéis; .card = um painel. Mesma família de .leituras/.leitura,
   mas usada como <div>, com mais respiro e borda de instrumento. */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:1rem;margin:1.4rem 0 2rem}
.card{background:var(--papel-2);border:1px solid var(--regua);padding:1.1rem 1.2rem;
  display:flex;flex-direction:column;gap:.35rem;position:relative}
.card .label{font-family:var(--grotesca);font-size:.66rem;font-weight:650;
  letter-spacing:.16em;text-transform:uppercase;color:var(--tinta-3)}
.card .value{font-family:var(--mono);font-variant-numeric:tabular-nums;
  font-size:clamp(1.6rem,3.2vw,2.2rem);font-weight:600;letter-spacing:-.02em;
  color:var(--tinta);line-height:1.15}
.card .muted{font-size:.78rem;line-height:1.5;color:var(--tinta-2);margin:0}

/* Estados semânticos — SÓ os três tons que o produto reconhece.
   Aparecem em <span>, <p>, <div>. Nunca inventar quarto tom. */
.ok{color:var(--selo);font-weight:600}
.warn{color:var(--latao);font-weight:600}
.bad{color:var(--oxido);font-weight:600}
.muted{color:var(--tinta-3)}
.muted small{color:var(--tinta-3)}

/* Célula de identificador em tabela: mono, tabular, à esquerda. Sem isto,
   claim_id e sequence herdam a serifa e ficam ilegíveis ao lado do resto. */
td.id{font-family:var(--mono);font-variant-numeric:tabular-nums;
  font-size:.82rem;letter-spacing:-.005em;color:var(--tinta-2);white-space:nowrap}

/* Lista de passos concretos ("O que precisa acontecer") — a única <ol> com
   estilo dedicado, para não parecer numeração de manual. */
ol.passos{padding-left:1.4rem;margin:.8rem 0 1.6rem;max-width:64ch}
ol.passos li{margin:.5rem 0;color:var(--tinta-2)}
ol.passos li b{color:var(--tinta)}

/* Nota interna de painel (não confundir com footer.the-eye global). */
.foot{font-size:.78rem;color:var(--tinta-3);margin:1rem 0 0;line-height:1.6;max-width:64ch}

/* Glossário de códigos de evento (corrente): mono à esquerda, prosa à direita. */
ul.legend{list-style:none;padding:0;margin:.6rem 0 1.4rem;display:grid;
  grid-template-columns:minmax(14rem,20rem) 1fr;gap:.35rem 1rem;font-size:.82rem}
ul.legend li{display:contents}
ul.legend li code{font-family:var(--mono);font-size:.78rem;color:var(--tinta);
  background:var(--papel-2);padding:.15rem .4rem;border-radius:2px}
ul.legend li span{color:var(--tinta-2);align-self:center}

/* Linhagem de evento (a peça-âncora da narrativa de proveniência): uma <div class="linha">
   com uma <div class="cadeia"> de nós encadeados e uma <div class="meta"> embaixo. */
.linha{padding:.9rem 0;border-bottom:1px solid var(--regua)}
.linha:last-child{border-bottom:0}
.cadeia{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem;font-size:.82rem}
.cadeia .no{display:inline-flex;align-items:center;padding:.32rem .6rem;
  border:1px solid var(--regua);background:var(--papel);border-radius:2px;
  font-family:var(--mono);font-size:.76rem;color:var(--tinta-2)}
.cadeia::after,.cadeia .no + .no::before{content:"→";color:var(--tinta-3);
  padding:0 .1rem;font-size:.72rem}
.cadeia::after{display:none}
.meta{font-family:var(--mono);font-size:.72rem;color:var(--tinta-3);
  margin-top:.35rem;letter-spacing:-.005em}

/* Aviso compacto (variante de .muted com sinal visual mínimo). */
.aviso{font-size:.82rem;color:var(--latao);margin:.8rem 0 1.4rem;
  padding-left:.8rem;border-left:2px solid var(--latao-clara);max-width:64ch}

/* Grelha de gráficos (benchmark): mesma família de .cards, mais respiro. */
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));
  gap:1.4rem;margin:1.4rem 0}
.chart{background:var(--papel-2);border:1px solid var(--regua);padding:1.1rem 1.2rem}
.chart h2{margin:0 0 .8rem;font-size:1.02rem}
.chart-svg{width:100%;height:auto;display:block}
.chart-svg text{font-family:var(--grotesca);fill:var(--tinta-2)}
.chart-svg rect{shape-rendering:crispEdges}

@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
@media (max-width: 640px){
  body{font-size:16px}
  .leituras{grid-template-columns:1fr 1fr}
  thead th,tbody td{padding-right:.75rem}
}
"""


def hash_fio(valor: str) -> str:
    """A assinatura: o hash como fio de borda. Prova usada como ornamento."""
    if not valor:
        return ""
    return f'<span class="hash-fio">{html.escape(valor)}</span>'


def leitura(rotulo: str, valor: Any, glosa: str = "", cor: str = "") -> str:
    """Uma leitura de instrumento: rótulo pequeno, número grande, glosa embaixo."""
    classe = f" {cor}" if cor else ""
    linha_glosa = f'<div class="glosa">{glosa}</div>' if glosa else ""
    return (
        f'<div class="leitura"><div class="rotulo">{html.escape(rotulo)}</div>'
        f'<div class="valor{classe}">{valor}</div>{linha_glosa}</div>'
    )


def estado(texto: str, tom: str = "latao") -> str:
    """Marca de estado. ``selo`` para verificado, ``latao`` para aberto."""
    return f'<span class="marca-estado e-{tom}">{html.escape(texto)}</span>'


# Favicon SVG embutido: circunferência + ponto = "o olho". Uma requisição a
# menos e zero bytes de rede. O tamanho longo é natureza de data URI escapado.
FAVICON = (  # noqa: E501 - data URI é longo por natureza; quebrar prejudica leitura
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Ccircle cx='16' cy='16' r='12' fill='none' stroke='%231F5C4A' stroke-width='2'/%3E"
    "%3Ccircle cx='16' cy='16' r='4' fill='%231F5C4A'/%3E%3C/svg%3E"
)


def pagina(
    *,
    titulo: str,
    corpo: str,
    rota: str = "",
    estatico: bool = False,
    local: str = "",
    descricao: str = "",
) -> str:
    """O invólucro único de toda página. Um tema, não dez cópias.

    ``descricao`` alimenta ``<meta name="description">`` e ``og:description`` —
    sem isso, um link do produto compartilhado renderiza preview vazio. O
    default é a tese; cada página passa a sua própria quando faz sentido.
    """
    from .navegacao import AVISO, barra

    marcador = f'<span class="local">{html.escape(local)}</span>' if local else ""
    desc = descricao or (
        "Mercados preditivos auditáveis. Probabilidade selada antes do fato, "
        "resolvida contra fonte oficial, verificável sem pedir licença."
    )
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta name="theme-color" content="#1F5C4A">
<meta property="og:title" content="{html.escape(titulo)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<link rel="icon" href="{FAVICON}">
<style>{TOKENS}{BASE}</style></head>
<body><main>
<header class="topo">
<span class="marca">ASUS <em>·</em> THE EYE</span>{marcador}
</header>
{barra(rota, estatico=estatico)}
{corpo}
<footer class="the-eye">{AVISO}
<br><br><small>© 2026 <strong>Mateus Menezes Figueiredo</strong> — ASUS THE EYE ·
plataforma de mercados preditivos auditáveis · AGPL-3.0-or-later</small></footer>
</main></body></html>"""
