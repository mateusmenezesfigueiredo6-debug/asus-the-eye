# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Site de apresentacao do vertical cannabis medicinal.

Este modulo existe para gerar, como funcoes puras, as paginas do site
fechado de demonstracao do projeto cannabis: vitrine de produtos FICTICIOS
(nomes inventados, selo visivel de demonstracao), P&D, captacao de medicos
prescritores, estudo de marca e contato. Nenhum dado aqui e real: precos,
produtos e numeros sao ilustrativos e declarados como tal em cada pagina,
em obediencia a regra de honestidade estatistica do projeto (nunca afirmar
o que nao foi medido).

O deploy e um Worker de assets estaticos gateado por codigo de acesso
(apps/cannabis-demo/); este modulo so produz HTML.
"""

from __future__ import annotations

BRAND = "Gota Verde"
BRAND_TAG = "Cannabis medicinal com prova, nao com promessa"

FONTES = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    "family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;"
    "0,9..144,600;1,9..144,400&"
    'family=Inter:wght@400;500;600&display=swap" rel="stylesheet">'
)

# Identidade clinica-editorial: fundo off-white quente, tinta escura,
# verde profundo como unico acento, linhas finas, paineis brancos sem
# sombra. Serifa display (Fraunces) para titulos, Inter para texto.
CSS_BASE = """
:root {
  --bg: #faf8f4; --panel: #ffffff; --line: #e4dfd4;
  --ink: #1a2420; --dim: #4c5a51; --dim2: #8a948c;
  --green: #1e5c40; --green2: #174a33; --sage: #7d9b87;
  --serif: 'Fraunces', Georgia, 'Times New Roman', serif;
  --sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body { background: var(--bg); color: var(--ink);
  font-family: var(--sans); font-weight: 400;
  line-height: 1.75; letter-spacing: 0.005em; }
a { color: var(--green); text-decoration: none;
  transition: color 0.2s ease; }
a:hover { color: var(--green2); text-decoration: underline;
  text-underline-offset: 3px; }
.wrap { max-width: 1140px; margin: 0 auto; padding: 0 32px; }
header.site { padding: 34px 0 30px; display: flex; align-items: center;
  justify-content: space-between; gap: 28px; flex-wrap: wrap;
  border-bottom: 1px solid var(--line); }
.logo { font-family: var(--serif); font-size: 1.4rem;
  letter-spacing: 0.02em; color: var(--ink); font-weight: 500; }
.logo small { display: block; font-family: var(--sans);
  font-size: 0.6rem; letter-spacing: 0.28em; color: var(--sage);
  text-transform: uppercase; margin-top: 3px; font-weight: 500; }
nav.menu { display: flex; gap: 28px; font-size: 0.7rem;
  letter-spacing: 0.2em; text-transform: uppercase; font-weight: 500; }
nav.menu a { color: var(--dim2); padding-bottom: 5px;
  border-bottom: 1px solid transparent; }
nav.menu a:hover { color: var(--green); text-decoration: none; }
nav.menu a.on { color: var(--green);
  border-bottom-color: var(--green); }
.hero { padding: 120px 0 84px; }
.hero .kicker, .kicker { font-size: 0.66rem; letter-spacing: 0.32em;
  text-transform: uppercase; color: var(--sage); font-weight: 600; }
.hero h1 { font-family: var(--serif); font-size: clamp(2.6rem, 5.4vw,
  4.4rem); font-weight: 400; line-height: 1.06; max-width: 860px;
  margin-top: 22px; letter-spacing: -0.01em; }
.hero h1 em { font-style: italic; color: var(--green); }
.hero p.lede { color: var(--dim); max-width: 600px; margin-top: 28px;
  font-size: 1.05rem; }
.cta-row { margin-top: 40px; display: flex; gap: 14px; flex-wrap: wrap; }
.btn { display: inline-block; padding: 14px 30px; border-radius: 0;
  font-size: 0.7rem; letter-spacing: 0.22em; text-transform: uppercase;
  font-weight: 600; }
.btn.solid { background: var(--green); color: #ffffff; }
.btn.solid:hover { background: var(--green2); color: #ffffff;
  text-decoration: none; }
.btn.ghost { border: 1px solid var(--ink); color: var(--ink); }
.btn.ghost:hover { border-color: var(--green); color: var(--green);
  text-decoration: none; }
.badge-demo { display: inline-block; border: 1px solid var(--sage);
  color: var(--green); background: var(--panel); font-size: 0.6rem;
  letter-spacing: 0.24em; text-transform: uppercase; padding: 6px 16px;
  margin-bottom: 30px; font-weight: 600; }
.stats { display: grid; grid-template-columns: repeat(auto-fit,
  minmax(200px, 1fr)); gap: 1px; background: var(--line);
  border-top: 1px solid var(--line); border-bottom: 1px solid
  var(--line); margin: 44px 0 0; }
.stats div { background: var(--bg); padding: 30px 26px 30px 0; }
.stats b { display: block; font-family: var(--serif); font-size: 2.3rem;
  font-weight: 400; color: var(--green); line-height: 1.15; }
.stats span { font-size: 0.68rem; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--dim2); font-weight: 500; }
.grid { display: grid; grid-template-columns: repeat(auto-fill,
  minmax(300px, 1fr)); gap: 28px; padding: 48px 0 96px; }
.card { background: var(--panel); border: 1px solid var(--line);
  padding: 30px; transition: border-color 0.25s ease; }
.card:hover { border-color: var(--sage); }
.card h3 { font-family: var(--serif); font-weight: 500;
  font-size: 1.5rem; margin-top: 6px; letter-spacing: -0.01em; }
.card .tipo { font-size: 0.6rem; color: var(--sage);
  letter-spacing: 0.26em; text-transform: uppercase; font-weight: 600; }
.card .preco { color: var(--green); font-family: var(--serif);
  font-size: 1.2rem; margin-top: 16px; font-weight: 500; }
.card p.desc { color: var(--dim); font-size: 0.88rem; margin-top: 10px; }
.card svg { width: 100%; height: 170px; margin-bottom: 20px; }
.selo { font-size: 0.58rem; color: var(--green);
  border: 1px dashed var(--sage); padding: 4px 10px;
  letter-spacing: 0.18em; font-weight: 600; }
section.bloco { border-top: 1px solid var(--line); padding: 88px 0; }
section.bloco .num { font-family: var(--serif); font-size: 0.9rem;
  color: var(--sage); letter-spacing: 0.3em; }
section.bloco h2 { font-family: var(--serif); font-weight: 400;
  font-size: clamp(1.8rem, 3.2vw, 2.6rem); margin: 12px 0 24px;
  letter-spacing: -0.01em; }
section.bloco p, section.bloco li { color: var(--dim); max-width: 720px;
  font-size: 0.96rem; }
section.bloco ul { padding-left: 22px; margin-top: 12px; }
section.bloco li { margin-bottom: 10px; }
section.bloco b { color: var(--ink); font-weight: 600; }
.duas { display: grid; grid-template-columns: repeat(auto-fit,
  minmax(300px, 1fr)); gap: 44px; }
table.tab { border-collapse: collapse; width: 100%; margin-top: 26px;
  font-size: 0.88rem; background: var(--panel);
  border: 1px solid var(--line); }
table.tab th, table.tab td { border: 1px solid var(--line);
  padding: 14px 16px; text-align: left; color: var(--dim);
  vertical-align: top; }
table.tab th { color: var(--ink); background: var(--bg);
  font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;
  font-size: 0.64rem; }
.pipeline { counter-reset: fase; margin-top: 30px; }
.pipeline .fase { display: flex; gap: 26px; padding: 26px 0;
  border-top: 1px solid var(--line); }
.pipeline .fase::before { counter-increment: fase;
  content: counter(fase, decimal-leading-zero);
  font-family: var(--serif); font-size: 1.5rem; color: var(--sage);
  min-width: 56px; }
.pipeline h4 { font-family: var(--serif); font-size: 1.25rem;
  font-weight: 500; }
.pipeline p { font-size: 0.9rem; }
.pipeline .status { font-size: 0.56rem; letter-spacing: 0.2em;
  text-transform: uppercase; color: var(--sage);
  border: 1px solid var(--line); padding: 3px 9px; font-weight: 600;
  vertical-align: middle; }
footer.site { border-top: 1px solid var(--line); padding: 40px 0 72px;
  color: var(--dim2); font-size: 0.78rem; }
.form-medico { max-width: 740px; margin-top: 30px; }
.form-medico .campo-linha { display: grid; grid-template-columns:
  repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
.form-medico label { display: block; font-size: 0.66rem;
  letter-spacing: 0.16em; text-transform: uppercase; color: var(--dim);
  font-weight: 600; }
.form-medico input, .form-medico select { display: block; width: 100%;
  margin-top: 8px; background: var(--panel); border: 1px solid
  var(--line); color: var(--ink); padding: 12px 13px; border-radius: 0;
  font-family: var(--sans); font-size: 0.95rem; }
.form-medico input:focus, .form-medico select:focus { outline: none;
  border-color: var(--green); }
.form-medico .check { display: flex; gap: 10px; align-items:
  flex-start; text-transform: none; letter-spacing: normal;
  font-size: 0.86rem; margin: 20px 0; color: var(--dim);
  font-weight: 400; }
.form-medico .check input { width: auto; margin-top: 4px;
  accent-color: var(--green); }
.form-medico button { cursor: pointer; border: 0; font-family:
  var(--sans); }
.form-medico .btn.ghost { border: 1px solid var(--ink);
  background: transparent; }
.crm-status { font-size: 0.86rem; min-height: 1.4em; margin: 4px 0; }
.crm-status.ok { color: var(--green); }
.crm-status.erro { color: #a33b3b; }
.mini-form { font-size: 0.78rem; color: var(--dim2); }
.faq details { border: 1px solid var(--line); background: var(--panel);
  margin-bottom: 12px; max-width: 740px; }
.faq summary { cursor: pointer; padding: 18px 22px;
  font-family: var(--serif); font-size: 1.1rem; color: var(--ink);
  list-style: none; font-weight: 500; }
.faq summary::before { content: "+ "; color: var(--sage); }
.faq details[open] summary::before { content: "- "; }
.faq details p { padding: 0 22px 18px; color: var(--dim);
  font-size: 0.92rem; }
.aviso { background: var(--panel); border: 1px solid var(--line);
  border-left: 2px solid var(--green); padding: 20px 24px;
  margin: 34px 0; color: var(--dim); font-size: 0.88rem;
  max-width: 740px; }
.paleta { display: flex; gap: 14px; margin: 20px 0; flex-wrap: wrap; }
.paleta div { width: 108px; height: 68px; border: 1px solid var(--line);
  display: flex; align-items: flex-end; padding: 7px; font-size: 0.58rem;
  letter-spacing: 0.06em; }
"""

PAGINAS = (
    ("index.html", "Inicio"),
    ("produtos.html", "Produtos"),
    ("pesquisa.html", "P&D"),
    ("medicos.html", "Para medicos"),
    ("autorizacao.html", "Autorizacao"),
    ("marca.html", "Marca"),
    ("contato.html", "Contato"),
)


def _frasco_svg(cor: str, rotulo: str) -> str:
    """Frasco estilizado desenhado em codigo — nenhuma foto copiada."""
    gid = cor.strip("#")
    # o rotulo tem 38px de largura: uma palavra por linha, sem vazar
    linhas = rotulo.split()[:3]
    y0 = 96 - 8 * len(linhas)
    texto = "".join(
        f'<text x="100" y="{y0 + 9 * i}" text-anchor="middle" '
        f'fill="#1a2420" font-size="6" font-family="Georgia, serif" '
        f'letter-spacing="0.6">{p}</text>'
        for i, p in enumerate(linhas)
    )
    return f"""<svg viewBox="0 0 200 170" xmlns="http://www.w3.org/2000/svg"
      role="img" aria-label="Ilustracao de frasco {rotulo}">
      <defs><linearGradient id="g{gid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{cor}" stop-opacity="0.92"/>
        <stop offset="1" stop-color="{cor}"/></linearGradient></defs>
      <line x1="30" y1="152" x2="170" y2="152" stroke="#e4dfd4"
        stroke-width="1"/>
      <rect x="86" y="18" width="28" height="16" fill="#1a2420"/>
      <rect x="86" y="32" width="28" height="3" fill="#7d9b87"/>
      <rect x="74" y="38" width="52" height="114" rx="4"
        fill="url(#g{gid})"/>
      <rect x="81" y="60" width="38" height="58" fill="#faf8f4"/>
      {texto}
      <text x="100" y="103" text-anchor="middle" fill="#8a948c"
        font-size="5" font-family="sans-serif"
        letter-spacing="1">DEMONSTRATIVO</text>
      <line x1="88" y1="110" x2="112" y2="110" stroke="#1e5c40"
        stroke-width="0.8"/>
    </svg>"""


# Produtos FICTICIOS. Nomes inventados; formatos comuns do mercado, sem
# imitar identidade visual ou nome de nenhuma marca real.
PRODUTOS = (
    (
        "Reserva 3000",
        "Oleo full spectrum",
        "CBD 3000 mg | 30 ml",
        "R$ 289 (ilustrativo)",
        "#1f4d33",
        "Extrato full spectrum em oleo MCT; laudo cromatografico por lote, verificavel pelo QR do rotulo.",
    ),
    (
        "Reserva 6000",
        "Oleo full spectrum",
        "CBD 6000 mg | 30 ml",
        "R$ 489 (ilustrativo)",
        "#173f2a",
        "Alta concentracao para terapias de manutencao com custo menor por miligrama.",
    ),
    (
        "Puro Isolado 1500",
        "Oleo isolado",
        "CBD 1500 mg | THC 0,0%",
        "R$ 199 (ilustrativo)",
        "#265c3d",
        "CBD isolado, sem THC detectavel — para quem tem restricao ocupacional ou teste toxicologico.",
    ),
    (
        "Capsulas 25",
        "Capsulas gastrorresistentes",
        "25 mg CBD por capsula | 30 unidades",
        "R$ 159 (ilustrativo)",
        "#2f4d1f",
        "Dose fixa diaria, sem sabor, com curva de liberacao previsivel.",
    ),
    (
        "Balsamo Recupera",
        "Topico",
        "CBD 500 mg | 60 g",
        "R$ 129 (ilustrativo)",
        "#4d3d1f",
        "Uso topico para desconforto muscular e articular localizado.",
    ),
    (
        "Noite 1:1",
        "Oleo balanceado",
        "CBD:THC 1:1 | 30 ml",
        "R$ 349 (ilustrativo)",
        "#1f3d4d",
        "Formula balanceada para dor e sono; dispensacao condicionada a receituario tipo B.",
    ),
    (
        "Linha Pet 600",
        "Veterinario",
        "CBD 600 mg | 30 ml",
        "R$ 149 (ilustrativo)",
        "#3d1f4d",
        "Uso veterinario mediante prescricao de medico veterinario.",
    ),
    (
        "Sublingual Spray",
        "Spray sublingual",
        "2,5 mg CBD por jato",
        "R$ 179 (ilustrativo)",
        "#4d1f2a",
        "Titulacao fina em jatos de 2,5 mg; absorcao sublingual rapida.",
    ),
)


def _shell(titulo: str, rota: str, corpo: str) -> str:
    nav = "".join(f'<a href="{arq}" class="{"on" if arq == rota else ""}">{nome}</a>' for arq, nome in PAGINAS)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{titulo} — {BRAND}</title>
<meta name="description" content="{BRAND}: cannabis medicinal com
evidencia. Laudo por lote, dispensacao condicionada a prescricao e
farmacovigilancia ativa. Material de apresentacao restrito.">
<meta property="og:title" content="{titulo} — {BRAND}">
<meta property="og:description" content="Cannabis medicinal com prova,
nao com promessa.">
<meta property="og:type" content="website">
<meta property="og:image" content="icone.svg">
{FONTES}
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icone.svg" type="image/svg+xml">
<meta name="theme-color" content="#faf8f4">
<style>{CSS_BASE}</style>
</head>
<body>
<div class="wrap">
<header class="site">
  <span class="logo">{BRAND}<small>cannabis medicinal com evidencia</small></span>
  <nav class="menu">{nav}</nav>
</header>
{corpo}
<footer class="site">
  <p>{BRAND} — material de apresentacao interna, acesso restrito por
  codigo. Todos os produtos, precos e numeros deste site sao FICTICIOS e
  ilustrativos; nada aqui e oferta de venda ou promessa terapeutica.
  Produtos a base de cannabis exigem prescricao medica e via legal de
  acesso (RDC 660/2022 ou produto autorizado pela ANVISA). Este site nao
  vende, nao indica tratamento e nao substitui consulta medica.</p>
</footer>
</div>
<script>
if ('serviceWorker' in navigator) {{
  navigator.serviceWorker.register('sw.js').catch(function () {{}});
}}
</script>
</body>
</html>"""


def index_page() -> str:
    corpo = f"""
<section class="hero">
  <span class="badge-demo">Apresentacao interna — dados ilustrativos</span>
  <h1>Cannabis medicinal com <em>prova</em>,<br>nao com promessa.</h1>
  <p class="lede">A {BRAND} esta sendo construida sobre uma tese simples:
  nesse mercado, quem provar origem, pureza e dispensacao correta — com
  evidencia que ninguem consegue reescrever depois — define o padrao.
  Cada lote com laudo, cada receita com registro, cada evento adverso com
  trilha permanente.</p>
  <div class="cta-row">
    <a class="btn solid" href="produtos.html">Vitrine demonstrativa</a>
    <a class="btn ghost" href="pesquisa.html">Pesquisa e desenvolvimento</a>
    <a class="btn ghost" href="medicos.html">Sou medico prescritor</a>
  </div>
  <div class="stats">
    <div><b>100%</b><span>lotes com laudo vinculado (meta de
    operacao)</span></div>
    <div><b>0</b><span>dispensacoes sem prescricao valida
    (regra, nao meta)</span></div>
    <div><b>24 h</b><span>prazo alvo de notificacao de evento
    adverso</span></div>
    <div><b>Aberta</b><span>trilha de auditoria verificavel por
    terceiros</span></div>
  </div>
</section>
<section class="bloco">
  <span class="num">01</span>
  <h2>O que sera diferente</h2>
  <div class="duas">
    <div>
      <ul>
        <li><b>Rastreabilidade da semente ao frasco.</b> Cada lote carrega
        origem, extracao, laudo e destino, encadeados por hash.</li>
        <li><b>Dispensacao condicionada.</b> Sem prescricao valida e
        atualizada, o sistema nao libera — nao existe excecao manual.</li>
      </ul>
    </div>
    <div>
      <ul>
        <li><b>Farmacovigilancia ativa.</b> Evento adverso notificado vira
        registro permanente e realimenta o corpo clinico.</li>
        <li><b>Honestidade estatistica.</b> Nenhum numero publicado sem
        metodo e fonte; o que nao foi medido nao e afirmado.</li>
      </ul>
    </div>
  </div>
  <div class="aviso">Fase atual: apresentacao e captacao de parceiros.
  Nao ha operacao comercial, estoque ou venda. O acesso a este material e
  restrito por codigo.</div>
</section>
<section class="bloco">
  <span class="num">02</span>
  <h2>Como vai funcionar, em quatro passos</h2>
  <div class="pipeline">
    <div class="fase"><div><h4>Consulta com prescritor</h4>
      <p>Telemedicina com medico de CRM ativo; a receita nasce digital e
      ja entra na trilha de auditoria.</p></div></div>
    <div class="fase"><div><h4>Produto com laudo</h4>
      <p>Cada lote com cromatografia de terceiros; o QR do rotulo abre o
      laudo antes do primeiro uso.</p></div></div>
    <div class="fase"><div><h4>Dispensacao condicionada</h4>
      <p>Sem prescricao valida o sistema nao libera — nao existe excecao
      manual.</p></div></div>
    <div class="fase"><div><h4>Acompanhamento continuo</h4>
      <p>Renovacao lembrada, efeito adverso notificado, historico que o
      paciente carrega consigo.</p></div></div>
  </div>
</section>
<section class="bloco">
  <span class="num">03</span>
  <h2>Perguntas diretas, respostas diretas</h2>
  <div class="faq">
    <details><summary>Isso e legal no Brasil?</summary><p>Sim, nas vias
    que a lei ja permite: importacao por paciente (RDC 660/2022),
    produtos autorizados em farmacia (RDC 327/2019) e telemedicina
    nacional (CFM 2.314/2022). Cultivo associativo, so com autorizacao
    judicial — e e assim que trabalharemos.</p></details>
    <details><summary>Preciso de receita?</summary><p>Sempre. Nenhum
    produto derivado de cannabis e dispensado sem prescricao de
    profissional com registro ativo, e o sistema trava sem ela.</p>
    </details>
    <details><summary>Como sei que o produto e puro?</summary><p>Cada
    lote tera laudo de laboratorio independente vinculado ao QR do
    rotulo. Sem laudo, o lote nao circula.</p></details>
    <details><summary>Voces prometem cura?</summary><p>Nao. Prometemos
    origem provada, dose certa e acompanhamento. Indicacao terapeutica e
    conversa entre voce e seu medico.</p></details>
    <details><summary>Quando comeca a operacao?</summary><p>Estamos em
    fase de apresentacao e estruturacao juridica. Deixe seu contato na
    aba Contato para ser avisado.</p></details>
  </div>
</section>"""
    return _shell("Inicio", "index.html", corpo)


def produtos_page() -> str:
    cards = "".join(
        f"""<div class="card">
        {_frasco_svg(cor, tipo.upper()[:18])}
        <span class="tipo">{tipo}</span>
        <h3>{nome}</h3>
        <p class="desc">{spec}</p>
        <p class="desc">{desc}</p>
        <p class="preco">{preco}</p>
        <p style="margin-top:12px"><span class="selo">PRODUTO
        DEMONSTRATIVO — NAO E OFERTA</span></p>
        </div>"""
        for nome, tipo, spec, preco, cor, desc in PRODUTOS
    )
    corpo = f"""
<section class="hero">
  <span class="badge-demo">Vitrine demonstrativa</span>
  <h1>A linha <em>{BRAND}</em> (ficticia)</h1>
  <p class="lede">Catalogo ilustrativo criado para apresentacao. Nomes,
  formulas e precos sao inventados; os formatos seguem o que o mercado
  regulado pratica. Nenhum item esta a venda.</p>
</section>
<div class="grid">{cards}</div>"""
    return _shell("Produtos", "produtos.html", corpo)


def pesquisa_page() -> str:
    corpo = f"""
<section class="hero">
  <span class="badge-demo">Pesquisa e desenvolvimento</span>
  <h1>P&D: a vantagem que <em>nao se copia</em></h1>
  <p class="lede">Produto se imita em seis meses. O que nao se imita e um
  corpo de evidencia proprio: dados de mundo real, formulacoes com curva
  de estabilidade medida e farmacovigilancia que aprende. O P&D da
  {BRAND} e desenhado para transformar cada paciente atendido em
  conhecimento auditavel.</p>
</section>
<section class="bloco">
  <span class="num">01</span>
  <h2>Linhas de pesquisa</h2>
  <table class="tab">
    <tr><th>Linha</th><th>Pergunta central</th><th>Entregavel</th></tr>
    <tr><td>Evidencia de mundo real (RWE)</td><td>Quais desfechos os
    pacientes de fato relatam, por indicacao e por formulacao?</td>
    <td>Registro longitudinal anonimizado, com consentimento e
    LGPD.</td></tr>
    <tr><td>Estabilidade e formulacao</td><td>Quanto o canabinoide degrada
    por matriz (oleo, capsula, topico) ao longo do tempo?</td>
    <td>Curvas de estabilidade por lote; validade dita pelo dado, nao
    pelo padrao do mercado.</td></tr>
    <tr><td>Farmacovigilancia computacional</td><td>Da para detectar
    sinal de evento adverso antes do relato clinico consolidar?</td>
    <td>Modelo de deteccao de sinal sobre a base de notificacoes.</td></tr>
    <tr><td>Genetica e cultivo (fase judicial)</td><td>Quais quimiotipos
    entregam o perfil canabinoide alvo com menor variancia?</td>
    <td>Banco de quimiotipos; so avanca com autorizacao judicial de
    cultivo.</td></tr>
    <tr><td>Economia do acesso</td><td>Qual o custo real por miligrama
    por via de acesso (importacao, farmacia, associacao)?</td>
    <td>Serie de precos publicada com metodo — util para paciente e
    para politica publica.</td></tr>
  </table>
</section>
<section class="bloco">
  <span class="num">02</span>
  <h2>Pipeline</h2>
  <div class="pipeline">
    <div class="fase"><div><h4>Protocolo e etica
      <span class="status">Em desenho</span></h4>
      <p>Protocolos de coleta de dados com consentimento livre e
      esclarecido; submissao a Comite de Etica em Pesquisa (CEP/CONEP)
      antes de qualquer dado de paciente.</p></div></div>
    <div class="fase"><div><h4>Parcerias academicas
      <span class="status">Prospeccao</span></h4>
      <p>Convenios com universidades e laboratorios analiticos para
      cromatografia, estabilidade e desenho estatistico independente.</p>
      </div></div>
    <div class="fase"><div><h4>Registro de mundo real
      <span class="status">Aguarda operacao</span></h4>
      <p>Cada dispensacao alimenta o registro longitudinal; desfechos
      relatados pelo paciente em instrumento validado.</p></div></div>
    <div class="fase"><div><h4>Publicacao aberta
      <span class="status">Compromisso</span></h4>
      <p>Resultados publicados com metodo e dado agregado — inclusive
      quando o resultado for nulo ou contrario ao nosso interesse.</p>
      </div></div>
  </div>
  <div class="aviso">Regra de honestidade: se o dado mostrar que uma
  formulacao nao supera a alternativa mais simples, publicamos assim
  mesmo. Credibilidade e o unico ativo que este mercado ainda nao
  tem.</div>
</section>"""
    return _shell("P&D", "pesquisa.html", corpo)


def medicos_page() -> str:
    corpo = f"""
<section class="hero">
  <span class="badge-demo">Captacao de prescritores</span>
  <h1>Prescreva com estrutura, <em>sem conflito</em></h1>
  <p class="lede">Buscamos medicos com CRM ativo, sem vinculo de
  exclusividade com outras plataformas, para compor o corpo clinico da
  {BRAND} — com remuneracao digna e nenhuma contrapartida que comprometa
  a autonomia da prescricao.</p>
</section>
<section class="bloco">
  <span class="num">01</span>
  <h2>Modelos de parceria (todos licitos)</h2>
  <table class="tab">
    <tr><th>Modelo</th><th>Como funciona</th></tr>
    <tr><td>Pagamento por consulta</td><td>O medico define o valor da
    consulta e recebe por atendimento realizado na plataforma; agenda e
    telemedicina por nossa conta.</td></tr>
    <tr><td>Hora clinica / retainer</td><td>Blocos de horas de
    atendimento ou valor mensal fixo por disponibilidade.</td></tr>
    <tr><td>Corpo clinico consultivo</td><td>Participacao no conselho
    cientifico e no P&D, com remuneracao por reuniao ou projeto.</td></tr>
  </table>
  <div class="aviso">Compromisso etico inegociavel: a {BRAND} NAO paga
  comissao por prescricao, por paciente encaminhado ou por volume de
  receita. Comissionar prescricao e vedado pelo Codigo de Etica Medica;
  proposta nesse sentido sera recusada e registrada.</div>
</section>
<section class="bloco">
  <span class="num">02</span>
  <h2>Manifestar interesse</h2>
  <p>Preencha os dados abaixo. O CRM e verificado em duas etapas: o
  formato e conferido aqui e a situacao do registro e checada no portal
  oficial do CFM antes de qualquer contrato.</p>
  <form id="form-medico" class="form-medico">
    <div class="campo-linha">
      <label>Nome completo
        <input type="text" name="nome" required autocomplete="name">
      </label>
      <label>Especialidade
        <input type="text" name="especialidade" required>
      </label>
    </div>
    <div class="campo-linha">
      <label>CRM (somente numeros)
        <input type="text" name="crm" required inputmode="numeric"
          pattern="[0-9]{{4,7}}" maxlength="7"
          title="4 a 7 digitos, sem letras">
      </label>
      <label>UF do CRM
        <select name="uf" required>
          <option value="">Selecione</option>
          <option>AC</option><option>AL</option><option>AP</option>
          <option>AM</option><option>BA</option><option>CE</option>
          <option>DF</option><option>ES</option><option>GO</option>
          <option>MA</option><option>MT</option><option>MS</option>
          <option>MG</option><option>PA</option><option>PB</option>
          <option>PR</option><option>PE</option><option>PI</option>
          <option>RJ</option><option>RN</option><option>RS</option>
          <option>RO</option><option>RR</option><option>SC</option>
          <option>SP</option><option>SE</option><option>TO</option>
        </select>
      </label>
      <label>Modelo de interesse
        <select name="modelo" required>
          <option value="">Selecione</option>
          <option>Pagamento por consulta</option>
          <option>Hora clinica / retainer</option>
          <option>Conselho cientifico</option>
        </select>
      </label>
    </div>
    <p id="crm-status" class="crm-status"></p>
    <p>
      <button type="button" class="btn ghost" id="btn-cfm">Conferir CRM
      no portal do CFM</button>
    </p>
    <label class="check">
      <input type="checkbox" name="crm_ok" required>
      Confirmo que o CRM informado esta ATIVO na consulta publica do CFM
      e que nao possuo vinculo de exclusividade com outra plataforma.
    </label>
    <p>
      <button type="submit" class="btn solid">Enviar manifestacao</button>
    </p>
    <p class="mini-form">O envio abre seu email com os dados preenchidos
    (nao armazenamos nada neste site de apresentacao). A verificacao
    definitiva do registro e refeita por nossa equipe no
    <a href="https://portal.cfm.org.br/busca-medicos" target="_blank"
    rel="noopener">portal do CFM</a> antes do contrato.</p>
  </form>
</section>
<script>
(function () {{
  var form = document.getElementById('form-medico');
  var status = document.getElementById('crm-status');
  function crmValido() {{
    var crm = form.crm.value.trim();
    var uf = form.uf.value;
    if (!/^[0-9]{{4,7}}$/.test(crm)) {{
      status.textContent = 'CRM invalido: use apenas numeros (4 a 7 '
        + 'digitos), sem letras ou pontos.';
      status.className = 'crm-status erro';
      return false;
    }}
    if (!uf) {{
      status.textContent = 'Selecione a UF do CRM.';
      status.className = 'crm-status erro';
      return false;
    }}
    status.textContent = 'Formato do CRM valido (' + crm + '/' + uf
      + '). Confira agora a situacao ATIVA no portal do CFM.';
    status.className = 'crm-status ok';
    return true;
  }}
  form.crm.addEventListener('blur', crmValido);
  form.uf.addEventListener('change', crmValido);
  document.getElementById('btn-cfm').addEventListener('click',
    function () {{
      if (!crmValido()) return;
      window.open('https://portal.cfm.org.br/busca-medicos', '_blank',
        'noopener');
    }});
  form.addEventListener('submit', function (e) {{
    e.preventDefault();
    if (!crmValido()) return;
    if (!form.crm_ok.checked) {{
      status.textContent = 'Marque a confirmacao de CRM ativo para '
        + 'enviar.';
      status.className = 'crm-status erro';
      return;
    }}
    var corpo = 'Nome: ' + form.nome.value
      + '%0ACRM: ' + form.crm.value.trim() + '/' + form.uf.value
      + '%0AEspecialidade: ' + form.especialidade.value
      + '%0AModelo de interesse: ' + form.modelo.value
      + '%0ADeclaro CRM ativo (conferido no portal do CFM) e ausencia '
      + 'de exclusividade com concorrentes.';
    location.href = 'mailto:medicos@example.invalid'
      + '?subject=' + encodeURIComponent('Interesse - corpo clinico ('
        + form.crm.value.trim() + '/' + form.uf.value + ')')
      + '&body=' + corpo;
  }});
}})();
</script>"""
    return _shell("Para medicos", "medicos.html", corpo)


def marca_page() -> str:
    corpo = """
<section class="hero">
  <span class="badge-demo">Estudo de marca</span>
  <h1>Nome, paleta e <em>postura</em></h1>
  <p class="lede">DECISAO 24/08/2026: a marca do vertical e
  <b>Gota Verde</b> — concreta (o produto e uma gota), facil e
  memoravel — com o descritor "cannabis medicinal com evidencia".
  "Greengo" foi avaliado e descartado: marca holandesa de sedas em
  uso desde 2008, associacao recreativa e confusao com "gringo".
  Conferencia no INPI (classes 5, 35, 42 e 44) pendente antes do
  registro.</p>
  <p class="lede">Direcao pedida pelo dono: sonoridade proxima de
  "Sinaloa" combinada com cannabis. Registro tecnico: "Sinaloa" literal
  carrega associacao imediata com cartel e e inviavel para uma marca de
  saude, juridica e reputacionalmente. As opcoes abaixo preservam a
  musicalidade sem a associacao.</p>
</section>
<section class="bloco">
  <span class="num">01</span>
  <h2>Nomes candidatos</h2>
  <table class="tab">
    <tr><th>Nome</th><th>Leitura</th><th>Risco de marca</th></tr>
    <tr><td>Cinala Verde (nome de estudo anterior)</td><td>Sonoridade proxima, sem geografia
    mexicana; "verde" ancora em saude e planta. E o nome usado neste
    estudo.</td><td>Baixo; verificar INPI antes de registrar.</td></tr>
    <tr><td>Sinua</td><td>Curto, exotico, memoravel.</td><td>Baixo;
    conferencia INPI pendente.</td></tr>
    <tr><td>Sinal Verde</td><td>Expressao nativa do portugues:
    autorizacao, caminho liberado.</td><td>Medio: expressao comum,
    registro mais dificil.</td></tr>
    <tr><td>Cannaloa</td><td>Fusao direta cannabis + sufixo -loa.</td>
    <td>Medio: mantem eco de Sinaloa.</td></tr>
  </table>
</section>
<section class="bloco">
  <span class="num">02</span>
  <h2>Paleta e tipografia</h2>
  <div class="paleta">
    <div style="background:#faf8f4;color:#4c5a51">#FAF8F4 fundo</div>
    <div style="background:#1a2420;color:#faf8f4">#1A2420 tinta</div>
    <div style="background:#1e5c40;color:#faf8f4">#1E5C40 verde</div>
    <div style="background:#7d9b87;color:#1a2420">#7D9B87 salvia</div>
    <div style="background:#e4dfd4;color:#1a2420">#E4DFD4 linha</div>
  </div>
  <p>Titulos em Fraunces (serifa editorial de eixo optico variavel);
  dados e rotulos em Inter. Tom de voz: sobrio, tecnico, sem promessa de
  cura — a marca afirma o que consegue provar.</p>
</section>"""
    return _shell("Marca", "marca.html", corpo)


def contato_page() -> str:
    corpo = """
<section class="hero">
  <h1>Contato</h1>
  <p class="lede">Material restrito. Para acesso, parcerias, imprensa ou
  P&D:</p>
</section>
<section class="bloco">
  <ul>
    <li>Geral: <a href="mailto:contato@example.invalid">
    contato@example.invalid</a></li>
    <li>Medicos: <a href="mailto:medicos@example.invalid">
    medicos@example.invalid</a></li>
    <li>Pesquisa: <a href="mailto:pd@example.invalid">
    pd@example.invalid</a></li>
  </ul>
  <div class="aviso">Enderecos de email sao provisorios (dominio
  example.invalid) ate a marca ser registrada e o dominio definitivo
  contratado.</div>
</section>"""
    return _shell("Contato", "contato.html", corpo)


def autorizacao_page() -> str:
    """Wizard do paciente: gera o pacote de autorizacao ANVISA pronto.

    Automacao ate a linha legal: o Gov.br nao tem API publica, entao o
    wizard coleta e formata tudo, envia o pacote a associacao (endpoint
    /api/autorizacao do Worker) e gera a versao para impressao; a
    submissao final no Gov.br e feita pelo despachante humano com a
    procuracao do associado.
    """
    corpo = """
<section class="hero">
  <span class="badge-demo">Importacao assistida — RDC 660/2022</span>
  <h1>Seu pedido de autorizacao, <em>sem dor de cabeca</em></h1>
  <p class="lede">Preencha uma unica vez. Nossa equipe conduz o cadastro
  no Gov.br como sua representante e devolve o protocolo. A autorizacao
  sai no SEU nome e vale 2 anos.</p>
</section>
<section class="bloco">
  <form id="wiz" class="form-medico">
    <h2 style="margin-top:0">1. Seus dados</h2>
    <div class="campo-linha">
      <label>Nome completo<input name="nome" required></label>
      <label>CPF<input name="cpf" required inputmode="numeric"></label>
      <label>Data de nascimento<input name="nascimento" type="date"
        required></label>
    </div>
    <div class="campo-linha">
      <label>Email<input name="email" type="email" required></label>
      <label>Telefone<input name="telefone" required></label>
      <label>Endereco completo<input name="endereco" required></label>
    </div>
    <h2>2. Receita medica</h2>
    <div class="campo-linha">
      <label>Nome do medico<input name="medico" required></label>
      <label>CRM<input name="crm" required inputmode="numeric"
        pattern="[0-9]{4,7}"></label>
      <label>UF do CRM<input name="uf" required maxlength="2"></label>
      <label>Data da receita<input name="dataReceita" type="date"
        required></label>
    </div>
    <h2>3. Produto prescrito</h2>
    <div class="campo-linha">
      <label>Produto (como esta na receita)
        <input name="produto" required></label>
      <label>Concentracao e posologia
        <input name="posologia" required></label>
      <label>Fornecedor pretendido (se souber)
        <input name="fornecedor"></label>
    </div>
    <label class="check">
      <input type="checkbox" name="consent" required>
      Autorizo a Associacao Gota Verde a tratar estes dados para conduzir
      meu pedido de autorizacao junto a ANVISA, como minha representante,
      nos termos da LGPD. Os dados nao serao usados para outro fim.
    </label>
    <p>
      <button type="submit" class="btn solid">Enviar e gerar o
      pacote</button>
      <button type="button" class="btn ghost" id="btn-imprimir"
        style="display:none">Imprimir / salvar PDF</button>
    </p>
    <p class="crm-status" id="wiz-status"></p>
    <p class="mini-form">O que acontece depois: em ate 1 dia util nossa
    equipe confere a receita, assina com voce a procuracao de
    representacao e protocola o pedido no Gov.br. Voce recebe o numero
    do protocolo e, na sequencia, a autorizacao (validade: 2 anos).
    Nenhum dado fica armazenado neste site.</p>
  </form>
  <div id="pacote" style="display:none"></div>
</section>
<script>
(function () {
  var form = document.getElementById('wiz');
  var status = document.getElementById('wiz-status');
  var pacote = document.getElementById('pacote');
  var btnImp = document.getElementById('btn-imprimir');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var d = {};
    new FormData(form).forEach(function (v, k) { d[k] = String(v); });
    var linhas = [
      ['Paciente', d.nome], ['CPF', d.cpf],
      ['Nascimento', d.nascimento], ['Email', d.email],
      ['Telefone', d.telefone], ['Endereco', d.endereco],
      ['Medico', d.medico + ' - CRM ' + d.crm + '/' + d.uf],
      ['Data da receita', d.dataReceita],
      ['Produto', d.produto], ['Posologia', d.posologia],
      ['Fornecedor', d.fornecedor || 'a definir'],
    ];
    pacote.innerHTML = '<h2>Pacote de autorizacao (previa)</h2>' +
      '<table class="tab">' + linhas.map(function (l) {
        return '<tr><th>' + l[0] + '</th><td>' + l[1] + '</td></tr>';
      }).join('') + '</table>' +
      '<p class="mini-form">Anexos a reunir: receita medica legivel, ' +
      'documento com foto, comprovante de residencia e procuracao ' +
      'assinada (enviaremos o modelo).</p>';
    pacote.style.display = 'block';
    btnImp.style.display = 'inline-block';
    fetch('/api/autorizacao', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(d),
    }).then(function (r) { return r.json(); }).then(function (j) {
      status.className = 'crm-status ok';
      status.textContent = j.encaminhado
        ? 'Pacote enviado a equipe. Voce recebera contato em ate 1 dia util.'
        : 'Pacote gerado (modo demonstracao - envio sera ativado no deploy).';
    }).catch(function () {
      status.className = 'crm-status ok';
      status.textContent =
        'Pacote gerado localmente (demonstracao, sem backend).';
    });
  });
  btnImp.addEventListener('click', function () { window.print(); });
})();
</script>"""
    return _shell("Autorizacao", "autorizacao.html", corpo)


def automacao_page() -> str:
    """Painel de disparos (admin, atras do gate): convites a medicos e
    empresas via endpoint /api/outreach, com opt-out automatico."""
    corpo = """
<section class="hero">
  <span class="badge-demo">Painel interno — disparos</span>
  <h1>Convites a medicos e <em>empresas</em></h1>
  <p class="lede">Cole a lista (uma linha por contato:
  nome;email;crm;tipo — tipo = medico ou empresa). O envio usa o
  template oficial do funil, com descadastro automatico e lista de
  supressao. Maximo de 100 por disparo.</p>
</section>
<section class="bloco">
  <form id="disp" class="form-medico">
    <label>Lista (nome;email;crm;tipo)
      <textarea name="lista" rows="8" style="width:100%;background:
      var(--panel);border:1px solid var(--line);color:var(--ink);
      padding:11px;border-radius:0;font-family:var(--sans)"
      placeholder="Maria Silva;maria@exemplo.com;123456;medico"></textarea>
    </label>
    <label class="check">
      <input type="checkbox" name="base" required>
      Declaro que esta lista tem base legal (contato profissional
      publico ou consentimento) e que os descadastros anteriores foram
      respeitados. Sem esta base, o disparo e spam e viola a LGPD.
    </label>
    <p><button type="submit" class="btn solid">Disparar</button></p>
    <p class="crm-status" id="disp-status"></p>
  </form>
</section>
<script>
(function () {
  var form = document.getElementById('disp');
  var status = document.getElementById('disp-status');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var linhas = form.lista.value.split('\\n').map(function (l) {
      return l.trim();
    }).filter(Boolean);
    var dest = linhas.map(function (l) {
      var p = l.split(';');
      return { nome: (p[0]||'').trim(), email: (p[1]||'').trim(),
               crm: (p[2]||'').trim(), tipo: (p[3]||'medico').trim() };
    }).filter(function (d) { return d.email.indexOf('@') > 0; });
    if (!dest.length) {
      status.className = 'crm-status erro';
      status.textContent = 'Nenhum email valido na lista.';
      return;
    }
    status.className = 'crm-status';
    status.textContent = 'Enviando ' + dest.length + ' convites...';
    fetch('/api/outreach', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ destinatarios: dest }),
    }).then(function (r) { return r.json(); }).then(function (j) {
      status.className = 'crm-status ok';
      status.textContent = j.configurado
        ? ('Enviados: ' + j.enviados + ' | descadastrados pulados: '
          + j.suprimidos + ' | total: ' + j.total)
        : ('Lote validado (' + j.total + ' contatos). Envio real sera '
          + 'ativado quando FROM_EMAIL for configurado no deploy.');
    }).catch(function () {
      status.className = 'crm-status ok';
      status.textContent = 'Lote validado localmente (' + dest.length
        + ' contatos) - modo demonstracao, sem backend.';
    });
  });
})();
</script>"""
    return _shell("Disparos", "automacao.html", corpo)


def manifest_webmanifest() -> str:
    return """{
  "name": "Gota Verde",
  "short_name": "Gota Verde",
  "start_url": "index.html",
  "display": "standalone",
  "background_color": "#faf8f4",
  "theme_color": "#faf8f4",
  "icons": [
    { "src": "icone.svg", "sizes": "any", "type": "image/svg+xml",
      "purpose": "any" }
  ]
}"""


def icone_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="24" fill="#faf8f4"/>
  <circle cx="64" cy="64" r="56" fill="none" stroke="#e4dfd4"
    stroke-width="2"/>
  <path d="M64 18C50 42 38 58 38 78a26 26 0 0 0 52 0C90 58 78 42 64 18z"
    fill="#1e5c40"/>
  <path d="M64 52c2.5 7 9 10.5 15 11.5-6 1.7-9.5 4.3-11 7.7
    4.2-0.8 7.6 0 10.2 2.5-4.2 0.9-7.6 2.6-9.3 5.1 2.5 0.9 4.2 2.6 5 5.1
    -3.4-1.7-6.7-2.5-9.4-1.7v8.6h-1.6v-8.6c-2.7-0.8-6 0-9.4 1.7
    0.8-2.5 2.5-4.2 5-5.1-1.7-2.5-5.1-4.2-9.3-5.1 2.6-2.5 6-3.3 10.2-2.5
    -1.5-3.4-5-6-11-7.7 6-1 12.5-4.5 15-11.5z" fill="#faf8f4"/>
</svg>"""


def sw_js() -> str:
    return """// Cache basico para o PWA da apresentacao; rede primeiro.
const CACHE = 'gotaverde-v2';
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then((r) => {
        const copia = r.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copia));
        return r;
      })
      .catch(() => caches.match(e.request))
  );
});
"""


def deck_page() -> str:
    """Deck de investidores em HTML: mesma narrativa do PPTX, um arquivo.

    Slides navegaveis por teclado (setas/espaco), clique ou botoes; sai no
    export atras do mesmo gate por codigo do Worker.
    """
    slides = (
        (
            "capa",
            f"""<p class="kicker">Apresentacao para investidores — agosto
            2026</p>
            <h1 class="mega">{BRAND}</h1>
            <p class="tag">Cannabis medicinal com <em>prova</em>, nao com
            promessa.</p>
            <p class="mini">Material interno e confidencial. Produtos,
            precos e numeros sao ilustrativos ate a operacao existir.</p>""",
        ),
        (
            "problema",
            """<p class="kicker">O problema</p>
            <h2>O paciente brasileiro paga caro por um mercado sem
            confianca</h2>
            <div class="tres">
            <div class="cx"><b>01</b><h3>Acesso fragmentado</h3>
            <p>Importacao, farmacia e associacoes convivem com precos que
            variam 5x para o mesmo miligrama.</p></div>
            <div class="cx"><b>02</b><h3>Confianca escassa</h3>
            <p>Laudos inacessiveis, rotulos sem verificacao e promessas
            terapeuticas sem evidencia.</p></div>
            <div class="cx"><b>03</b><h3>Medico desassistido</h3>
            <p>Prescritores sem estrutura de acompanhamento e expostos a
            propostas antieticas de comissao.</p></div>
            </div>""",
        ),
        (
            "mercado",
            """<p class="kicker">Mercado</p>
            <h2>Um mercado legal que ja existe e so cresce</h2>
            <ul>
            <li>Desde 2015 a ANVISA autoriza importacao por pessoa fisica;
            a RDC 660/2022 simplificou o rito (autorizacao vale 2
            anos).</li>
            <li>Produtos nacionais autorizados (RDC 327/2019) ja sao
            vendidos em farmacia com receita.</li>
            <li>Associacoes de pacientes somam dezenas de milhares de
            associados (ABRACE declara 35 mil+).</li>
            <li>Plataformas privadas reportam centenas de prescritores
            ativos.</li>
            </ul>
            <p class="mini">Fontes: anvisa.gov.br; abrace.com.br;
            levantamento proprio (24/08/2026). Nao publicamos projecoes de
            TAM sem metodo.</p>""",
        ),
        (
            "tese",
            """<p class="kicker">A tese</p>
            <h2 class="mega2">Produto se copia.<br><em>Confianca auditavel,
            nao.</em></h2>
            <p>A Gota Verde nasce dentro de uma plataforma de evidencia
            auditavel (THE EYE): cada evento relevante — laudo, prescricao,
            dispensacao, efeito adverso — vira registro encadeado por hash
            que nem os fundadores conseguem reescrever. No unico mercado de
            saude onde a desconfianca e a regra, isso e o produto.</p>""",
        ),
        (
            "plataforma",
            """<p class="kicker">Produto — plataforma</p>
            <h2>Tres travas que o mercado nao tem</h2>
            <div class="tres">
            <div class="cx"><b>1</b><h3>Laudo por lote</h3><p>Cromatografia
            de terceiros vinculada ao QR do rotulo.</p></div>
            <div class="cx"><b>2</b><h3>Dispensacao condicionada</h3>
            <p>Sem prescricao valida o sistema nao libera; nao existe
            excecao manual.</p></div>
            <div class="cx"><b>3</b><h3>Farmacovigilancia ativa</h3>
            <p>Evento adverso vira registro permanente e realimenta
            prescritores e P&D.</p></div>
            </div>""",
        ),
        (
            "vitrine",
            """<p class="kicker">Produto — linha demonstrativa</p>
            <h2>A linha Gota Verde (ficticia, para apresentacao)</h2>
            <p>Oito SKUs ilustrativos — oleos full spectrum e isolados,
            capsulas, topico, balanceado 1:1, veterinario e spray
            sublingual — todos com selo DEMONSTRATIVO e precos marcados
            como ilustrativos. A vitrine completa esta na aba Produtos
            deste site.</p>""",
        ),
        (
            "tecnologia",
            """<p class="kicker">Tecnologia</p>
            <h2>Herdamos a infraestrutura, nao a construimos do zero</h2>
            <ul>
            <li>Cadeia de evidencia (hash chain + Merkle) ja em producao no
            THE EYE, com verificador publico de codigo aberto (AGPL).</li>
            <li>Site gateado por codigo (Worker + PWA) e app Expo para as
            lojas ja construidos.</li>
            <li>O investimento vai para operacao e P&D, nao para
            infraestrutura basica.</li>
            </ul>""",
        ),
        (
            "pd",
            """<p class="kicker">Pesquisa e desenvolvimento</p>
            <h2>P&D: a vantagem que nao se copia</h2>
            <ul>
            <li>Evidencia de mundo real — registro longitudinal com
            consentimento e LGPD.</li>
            <li>Estabilidade e formulacao — validade dita pelo dado.</li>
            <li>Farmacovigilancia computacional — deteccao de sinal.</li>
            <li>Genetica e cultivo — so com autorizacao judicial.</li>
            <li>Economia do acesso — custo por miligrama com metodo.</li>
            </ul>
            <p class="mini">Resultado nulo ou contrario tambem e publicado.
            Dado de paciente passa antes por CEP/CONEP.</p>""",
        ),
        (
            "modelo",
            """<p class="kicker">Modelo de negocio (ilustrativo)</p>
            <h2>Tres motores de receita, um funil so</h2>
            <div class="tres">
            <div class="cx"><b>F1</b><h3>Consultas</h3><p>Take rate sobre
            telemedicina com prescritores parceiros.</p></div>
            <div class="cx"><b>F2</b><h3>Assinatura do paciente</h3>
            <p>Acompanhamento, renovacao e farmacovigilancia como
            servico.</p></div>
            <div class="cx"><b>F3</b><h3>Operacao associativa</h3>
            <p>Fornecimento sem lucro via associacao + auditoria para o
            setor.</p></div>
            </div>
            <p class="mini">Sem projecoes neste deck: ainda nao ha operacao
            para calibra-las.</p>""",
        ),
        (
            "gtm",
            """<p class="kicker">Go-to-market</p>
            <h2>Primeiro o medico, depois o paciente</h2>
            <ul>
            <li>Funil de prescritores desenhado: triagem por CRM ativo,
            cadencia multicanal com opt-out e LGPD, tres modelos licitos de
            remuneracao.</li>
            <li><em>Nunca comissao por prescricao</em> — vedada pelo CEM; a
            recusa formal disso e argumento de recrutamento.</li>
            <li>Paciente chega pelo medico e por conteudo educacional, nao
            por promessa de cura.</li>
            </ul>""",
        ),
        (
            "regulatorio",
            """<p class="kicker">Regulatorio</p>
            <h2>Sabemos exatamente onde e a linha</h2>
            <div class="duas-col">
            <div><h3 class="ok">O que a lei ja permite</h3><ul>
            <li>Importacao por paciente (RDC 660/2022)</li>
            <li>Produtos nacionais em farmacia (RDC 327/2019)</li>
            <li>Telemedicina nacional (CFM 2.314/2022)</li>
            <li>Associacoes com autorizacao judicial de cultivo</li>
            </ul></div>
            <div><h3 class="nao">O que nao fazemos</h3><ul>
            <li>Venda sem prescricao ou fora da via legal</li>
            <li>Comissao por prescricao (vedada pelo CEM)</li>
            <li>Promessa terapeutica em publicidade</li>
            <li>Cultivo sem autorizacao judicial</li>
            </ul></div>
            </div>""",
        ),
        (
            "roadmap",
            """<p class="kicker">Roadmap</p>
            <h2>Quatro fases, cada uma paga a seguinte</h2>
            <div class="tres" style="grid-template-columns:repeat(4,1fr)">
            <div class="cx"><b>AGORA</b><h3>Apresentacao</h3><p>Site
            gateado, deck, estatuto pronto, funil desenhado.</p></div>
            <div class="cx"><b>0-6 M</b><h3>Associacao</h3><p>Cartorio,
            CNPJ, corpo clinico, primeiras consultas.</p></div>
            <div class="cx"><b>6-18 M</b><h3>Operacao</h3><p>Dispensacao
            auditada; acao de cultivo protocolada.</p></div>
            <div class="cx"><b>18 M+</b><h3>P&D em escala</h3><p>Registro
            de mundo real publicando.</p></div>
            </div>""",
        ),
        (
            "time",
            """<p class="kicker">Time</p>
            <h2>Os cargos estao definidos; os nomes, em conversa</h2>
            <div class="tres">
            <div class="cx"><h3>Presidente / CEO</h3><p>____________</p></div>
            <div class="cx"><h3>Diretor(a) Medico(a)</h3><p>____________</p></div>
            <div class="cx"><h3>Diretor(a) de Tecnologia</h3><p>____________</p></div>
            <div class="cx"><h3>Diretor(a) Juridico(a)</h3><p>____________</p></div>
            <div class="cx"><h3>Diretor(a) de P&D</h3><p>____________</p></div>
            <div class="cx"><h3>Diretor(a) Comercial</h3><p>____________</p></div>
            </div>""",
        ),
        (
            "convite",
            """<h2 class="mega2">O convite</h2>
            <p class="tag">Buscamos socios que entendam que, neste mercado,
            integridade nao e discurso — e o unico fosso defensavel.</p>
            <p>Captacao alvo: R$ ____________ &nbsp;|&nbsp; Instrumento:
            ____________ &nbsp;|&nbsp; Contato: ____________</p>
            <p class="mini">Este material nao constitui oferta publica de
            valores mobiliarios. Produtos e numeros sao ilustrativos; nao
            ha operacao comercial nesta data.</p>""",
        ),
    )
    corpo_slides = "".join(
        f'<section class="slide" id="s{i}">{html}<span class="pg">{i + 1:02d} / {len(slides):02d}</span></section>'
        for i, (_, html) in enumerate(slides)
    )
    css_deck = """
.slide { min-height: 100vh; display: none; flex-direction: column;
  justify-content: center; padding: 6vh 8vw; position: relative; }
.slide.on { display: flex; }
.slide h2 { font-family: var(--serif); font-weight: 400;
  font-size: clamp(2rem, 4.2vw, 3.2rem); margin: 16px 0 28px;
  max-width: 920px; letter-spacing: -0.01em; }
.slide h2 em, .slide .tag em { font-style: italic; color: var(--green); }
.mega { font-family: var(--serif); font-size: clamp(3.2rem, 8vw, 5.6rem);
  letter-spacing: -0.02em; color: var(--ink); font-weight: 400; }
.mega2 { font-family: var(--serif); font-weight: 400;
  font-size: clamp(2.3rem, 5vw, 3.8rem); letter-spacing: -0.01em; }
.tag { font-family: var(--serif); font-size: 1.5rem; font-style: italic;
  margin: 20px 0; max-width: 720px; color: var(--dim); }
.mini { color: var(--dim2); font-size: 0.8rem; margin-top: 30px;
  max-width: 720px; }
.slide ul { padding-left: 22px; max-width: 780px; }
.slide li { color: var(--dim); margin-bottom: 12px; font-size: 1rem; }
.slide p { color: var(--dim); max-width: 780px; }
.tres { display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 22px; margin-top: 10px; }
.cx { background: var(--panel); border: 1px solid var(--line);
  padding: 26px; }
.cx b { font-family: var(--serif); color: var(--sage);
  font-size: 1.35rem; }
.cx h3 { font-family: var(--serif); font-weight: 500;
  font-size: 1.25rem; margin: 8px 0; }
.cx p { font-size: 0.88rem; }
.duas-col { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
.duas-col h3 { font-family: var(--serif); font-weight: 500;
  margin-bottom: 10px; }
.ok { color: var(--green); } .nao { color: #7a5a1e; }
.pg { position: absolute; bottom: 3vh; right: 8vw;
  font-family: var(--serif); color: var(--sage); font-size: 0.85rem; }
.nav-deck { position: fixed; bottom: 3vh; left: 8vw; display: flex;
  gap: 10px; z-index: 5; }
.nav-deck button { background: var(--panel); color: var(--ink);
  border: 1px solid var(--line); padding: 9px 20px; cursor: pointer;
  font-family: var(--sans); letter-spacing: 0.14em; font-size: 0.68rem;
  text-transform: uppercase; font-weight: 600; }
.nav-deck button:hover { border-color: var(--green);
  color: var(--green); }
@media (max-width: 760px) { .tres, .duas-col {
  grid-template-columns: 1fr !important; } }
"""
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Deck de investidores — {BRAND}</title>
{FONTES}
<meta name="theme-color" content="#faf8f4">
<style>{CSS_BASE}{css_deck}</style>
</head>
<body>
{corpo_slides}
<div class="nav-deck">
  <button id="prev" type="button">Anterior</button>
  <button id="next" type="button">Proximo</button>
  <button type="button" onclick="location.href='index.html'">Sair</button>
</div>
<script>
(function () {{
  var slides = document.querySelectorAll('.slide');
  var i = 0;
  function mostra(n) {{
    i = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach(function (s, k) {{
      s.classList.toggle('on', k === i);
    }});
  }}
  document.getElementById('next').onclick = function () {{ mostra(i + 1); }};
  document.getElementById('prev').onclick = function () {{ mostra(i - 1); }};
  document.addEventListener('keydown', function (e) {{
    if (e.key === 'ArrowRight' || e.key === ' ') mostra(i + 1);
    if (e.key === 'ArrowLeft') mostra(i - 1);
  }});
  mostra(0);
}})();
</script>
</body>
</html>"""


def exportar(destino: str = "dist-cannabis") -> dict:
    """Escreve o site completo em `destino` e devolve o que foi gerado."""
    import pathlib

    raiz = pathlib.Path(destino)
    raiz.mkdir(parents=True, exist_ok=True)
    arquivos = {
        "index.html": index_page(),
        "produtos.html": produtos_page(),
        "pesquisa.html": pesquisa_page(),
        "medicos.html": medicos_page(),
        "marca.html": marca_page(),
        "contato.html": contato_page(),
        "autorizacao.html": autorizacao_page(),
        "automacao.html": automacao_page(),
        "deck.html": deck_page(),
        "manifest.webmanifest": manifest_webmanifest(),
        "icone.svg": icone_svg(),
        "sw.js": sw_js(),
    }
    for nome, conteudo in arquivos.items():
        (raiz / nome).write_text(conteudo, encoding="utf-8")
    return {"gerados": sorted(arquivos)}


if __name__ == "__main__":
    import sys

    alvo = sys.argv[1] if len(sys.argv) > 1 else "dist-cannabis"
    print(exportar(alvo))
