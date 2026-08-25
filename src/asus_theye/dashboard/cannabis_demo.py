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
    "family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&"
    'family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">'
)

# Identidade high end: verde-floresta profundo, dourado envelhecido,
# marfim; serifa display para titulos, sans geometrica para dados.
CSS_BASE = """
:root {
  --bg: #070b08; --bg2: #0b120d; --panel: #0f1811; --line: #1c2a1f;
  --line2: #2a3d2e; --ink: #ede9dd; --dim: #97a698; --dim2: #6b7a6c;
  --green: #58c47f; --gold: #c9a44a; --gold2: #e6cf8e;
  --serif: 'Cormorant Garamond', Georgia, 'Times New Roman', serif;
  --sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body { background:
    radial-gradient(1200px 600px at 80% -10%, #10241636, transparent),
    radial-gradient(900px 500px at -10% 30%, #1a121f2e, transparent),
    var(--bg);
  color: var(--ink); font-family: var(--sans); font-weight: 300;
  line-height: 1.75; letter-spacing: 0.01em; }
a { color: var(--green); text-decoration: none;
  transition: color 0.2s ease; }
a:hover { color: var(--gold2); }
.wrap { max-width: 1120px; margin: 0 auto; padding: 0 28px; }
header.site { padding: 26px 0; display: flex; align-items: center;
  justify-content: space-between; gap: 28px; flex-wrap: wrap;
  border-bottom: 1px solid var(--line); }
.logo { font-family: var(--serif); font-size: 1.5rem;
  letter-spacing: 0.28em; color: var(--gold2);
  text-transform: uppercase; font-weight: 500; }
.logo small { display: block; font-family: var(--sans);
  font-size: 0.58rem; letter-spacing: 0.34em; color: var(--dim2);
  margin-top: 2px; }
nav.menu { display: flex; gap: 26px; font-size: 0.72rem;
  letter-spacing: 0.18em; text-transform: uppercase; font-weight: 400; }
nav.menu a { color: var(--dim); padding-bottom: 4px;
  border-bottom: 1px solid transparent; }
nav.menu a.on { color: var(--gold2);
  border-bottom-color: var(--gold); }
.hero { padding: 110px 0 70px; }
.hero .kicker, .kicker { font-size: 0.68rem; letter-spacing: 0.3em;
  text-transform: uppercase; color: var(--gold); font-weight: 500; }
.hero h1 { font-family: var(--serif); font-size: clamp(2.4rem, 5vw,
  3.9rem); font-weight: 500; line-height: 1.12; max-width: 800px;
  margin-top: 18px; }
.hero h1 em { font-style: italic; color: var(--gold2); }
.hero p.lede { color: var(--dim); max-width: 620px; margin-top: 22px;
  font-size: 1.02rem; }
.cta-row { margin-top: 34px; display: flex; gap: 16px; flex-wrap: wrap; }
.btn { display: inline-block; padding: 13px 28px; border-radius: 2px;
  font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase;
  font-weight: 500; }
.btn.solid { background: var(--gold); color: #14100a; }
.btn.solid:hover { background: var(--gold2); color: #14100a; }
.btn.ghost { border: 1px solid var(--line2); color: var(--ink); }
.btn.ghost:hover { border-color: var(--gold); color: var(--gold2); }
.badge-demo { display: inline-block; border: 1px solid var(--gold);
  color: var(--gold); font-size: 0.62rem; letter-spacing: 0.22em;
  text-transform: uppercase; padding: 5px 14px; border-radius: 2px;
  margin-bottom: 26px; font-weight: 500; }
.stats { display: grid; grid-template-columns: repeat(auto-fit,
  minmax(200px, 1fr)); gap: 1px; background: var(--line);
  border: 1px solid var(--line); margin: 30px 0 0; }
.stats div { background: var(--bg2); padding: 26px 24px; }
.stats b { display: block; font-family: var(--serif); font-size: 2rem;
  font-weight: 500; color: var(--gold2); }
.stats span { font-size: 0.72rem; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--dim2); }
.grid { display: grid; grid-template-columns: repeat(auto-fill,
  minmax(320px, 1fr)); gap: 26px; padding: 44px 0 80px; }
.card { background: linear-gradient(180deg, var(--panel), var(--bg2));
  border: 1px solid var(--line); border-radius: 4px; padding: 28px;
  transition: border-color 0.25s ease, transform 0.25s ease; }
.card:hover { border-color: var(--gold); transform: translateY(-3px); }
.card h3 { font-family: var(--serif); font-weight: 500;
  font-size: 1.45rem; margin-top: 4px; }
.card .tipo { font-size: 0.62rem; color: var(--gold);
  letter-spacing: 0.24em; text-transform: uppercase; font-weight: 500; }
.card .preco { color: var(--gold2); font-family: var(--serif);
  font-size: 1.25rem; margin-top: 14px; }
.card p.desc { color: var(--dim); font-size: 0.88rem; margin-top: 10px; }
.card svg { width: 100%; height: 170px; margin-bottom: 18px; }
.selo { font-size: 0.6rem; color: var(--gold);
  border: 1px dashed var(--gold); padding: 3px 9px; border-radius: 2px;
  letter-spacing: 0.16em; font-weight: 500; }
section.bloco { border-top: 1px solid var(--line); padding: 76px 0; }
section.bloco .num { font-family: var(--serif); font-size: 0.95rem;
  color: var(--gold); letter-spacing: 0.2em; }
section.bloco h2 { font-family: var(--serif); font-weight: 500;
  font-size: clamp(1.7rem, 3vw, 2.4rem); margin: 10px 0 20px; }
section.bloco p, section.bloco li { color: var(--dim); max-width: 740px;
  font-size: 0.95rem; }
section.bloco ul { padding-left: 22px; margin-top: 12px; }
section.bloco li { margin-bottom: 8px; }
.duas { display: grid; grid-template-columns: repeat(auto-fit,
  minmax(300px, 1fr)); gap: 40px; }
table.tab { border-collapse: collapse; width: 100%; margin-top: 22px;
  font-size: 0.86rem; }
table.tab th, table.tab td { border: 1px solid var(--line);
  padding: 13px 15px; text-align: left; color: var(--dim);
  vertical-align: top; }
table.tab th { color: var(--gold2); background: var(--panel);
  font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase;
  font-size: 0.68rem; }
.pipeline { counter-reset: fase; margin-top: 26px; }
.pipeline .fase { display: flex; gap: 22px; padding: 22px 0;
  border-top: 1px solid var(--line); }
.pipeline .fase::before { counter-increment: fase;
  content: counter(fase, decimal-leading-zero);
  font-family: var(--serif); font-size: 1.6rem; color: var(--gold);
  min-width: 52px; }
.pipeline h4 { font-family: var(--serif); font-size: 1.2rem;
  font-weight: 500; }
.pipeline p { font-size: 0.88rem; }
.pipeline .status { font-size: 0.6rem; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--dim2);
  border: 1px solid var(--line2); padding: 2px 8px; border-radius: 2px; }
footer.site { border-top: 1px solid var(--line); padding: 34px 0 60px;
  color: var(--dim2); font-size: 0.76rem; }
.form-medico { max-width: 740px; margin-top: 26px; }
.form-medico .campo-linha { display: grid; grid-template-columns:
  repeat(auto-fit, minmax(200px, 1fr)); gap: 18px; margin-bottom: 18px; }
.form-medico label { display: block; font-size: 0.72rem;
  letter-spacing: 0.12em; text-transform: uppercase; color: var(--dim);
  font-weight: 500; }
.form-medico input, .form-medico select { display: block; width: 100%;
  margin-top: 7px; background: var(--bg2); border: 1px solid
  var(--line2); color: var(--ink); padding: 11px 12px; border-radius:
  2px; font-family: var(--sans); font-size: 0.95rem; }
.form-medico input:focus, .form-medico select:focus { outline: none;
  border-color: var(--gold); }
.form-medico .check { display: flex; gap: 10px; align-items:
  flex-start; text-transform: none; letter-spacing: normal;
  font-size: 0.85rem; margin: 18px 0; color: var(--dim); }
.form-medico .check input { width: auto; margin-top: 4px; }
.form-medico button { cursor: pointer; border: 0; font-family:
  var(--sans); }
.form-medico .btn.ghost { border: 1px solid var(--line2);
  background: transparent; }
.crm-status { font-size: 0.85rem; min-height: 1.4em; margin: 4px 0; }
.crm-status.ok { color: var(--green); }
.crm-status.erro { color: #d97676; }
.mini-form { font-size: 0.78rem; color: var(--dim2); }
.aviso { background: var(--panel); border-left: 2px solid var(--gold);
  padding: 18px 22px; margin: 30px 0; color: var(--dim);
  font-size: 0.86rem; max-width: 740px; }
.paleta { display: flex; gap: 14px; margin: 18px 0; flex-wrap: wrap; }
.paleta div { width: 104px; height: 64px; border-radius: 3px;
  display: flex; align-items: flex-end; padding: 6px; font-size: 0.58rem;
  letter-spacing: 0.06em; }
"""

PAGINAS = (
    ("index.html", "Inicio"),
    ("produtos.html", "Produtos"),
    ("pesquisa.html", "P&D"),
    ("medicos.html", "Para medicos"),
    ("marca.html", "Marca"),
    ("contato.html", "Contato"),
)


def _frasco_svg(cor: str, rotulo: str) -> str:
    """Frasco estilizado desenhado em codigo — nenhuma foto copiada."""
    return f"""<svg viewBox="0 0 200 170" xmlns="http://www.w3.org/2000/svg"
      role="img" aria-label="Ilustracao de frasco {rotulo}">
      <defs><linearGradient id="g{cor.strip("#")}" x1="0" y1="0" x2="0"
        y2="1"><stop offset="0" stop-color="{cor}"/>
        <stop offset="1" stop-color="#0b120d"/></linearGradient></defs>
      <ellipse cx="100" cy="152" rx="46" ry="7" fill="#000" opacity="0.4"/>
      <rect x="84" y="16" width="32" height="18" rx="3" fill="#1c1a14"/>
      <rect x="84" y="30" width="32" height="4" fill="#c9a44a"/>
      <rect x="72" y="36" width="56" height="112" rx="9"
        fill="url(#g{cor.strip("#")})" stroke="#2a3d2e"
        stroke-width="0.6"/>
      <rect x="79" y="62" width="42" height="56" rx="3" fill="#070b08"
        opacity="0.72"/>
      <text x="100" y="84" text-anchor="middle" fill="#e6cf8e"
        font-size="8.5" font-family="Georgia, serif"
        letter-spacing="1.4">{rotulo}</text>
      <text x="100" y="99" text-anchor="middle" fill="#97a698"
        font-size="6" font-family="sans-serif"
        letter-spacing="1.2">DEMONSTRATIVO</text>
      <line x1="86" y1="107" x2="114" y2="107" stroke="#c9a44a"
        stroke-width="0.6"/>
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
{FONTES}
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icone.svg" type="image/svg+xml">
<meta name="theme-color" content="#070b08">
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
    <div style="background:#070b08;color:#97a698">#070B08 fundo</div>
    <div style="background:#1f4d33;color:#ede9dd">#1F4D33 verde</div>
    <div style="background:#58c47f;color:#070b08">#58C47F acento</div>
    <div style="background:#c9a44a;color:#070b08">#C9A44A dourado</div>
    <div style="background:#ede9dd;color:#070b08">#EDE9DD marfim</div>
  </div>
  <p>Titulos em Cormorant Garamond (serifa de farmacia premium); dados e
  rotulos em Inter. Tom de voz: sobrio, tecnico, sem promessa de cura —
  a marca afirma o que consegue provar.</p>
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


def manifest_webmanifest() -> str:
    return """{
  "name": "Gota Verde",
  "short_name": "Gota Verde",
  "start_url": "index.html",
  "display": "standalone",
  "background_color": "#070b08",
  "theme_color": "#070b08",
  "icons": [
    { "src": "icone.svg", "sizes": "any", "type": "image/svg+xml",
      "purpose": "any" }
  ]
}"""


def icone_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="24" fill="#070b08"/>
  <path d="M64 14C48 40 34 58 34 80a30 30 0 0 0 60 0C94 58 80 40 64 14z"
    fill="#1f4d33" stroke="#58c47f" stroke-width="3"/>
  <path d="M64 52c3 8 11 12 18 13-7 2-11 5-13 9 5-1 9 0 12 3
    -5 1-9 3-11 6 3 1 5 3 6 6-4-2-8-3-11-2v10h-2V87
    c-3-1-7 0-11 2 1-3 3-5 6-6-2-3-6-5-11-6 3-3 7-4 12-3
    -2-4-6-7-13-9 7-1 15-5 18-13z" fill="#e6cf8e"/>
  <circle cx="64" cy="64" r="58" fill="none" stroke="#c9a44a"
    stroke-width="2"/>
</svg>"""


def sw_js() -> str:
    return """// Cache basico para o PWA da apresentacao; rede primeiro.
const CACHE = 'gotaverde-v1';
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
.slide h2 { font-family: var(--serif); font-weight: 500;
  font-size: clamp(1.9rem, 4vw, 3rem); margin: 14px 0 26px;
  max-width: 900px; }
.slide h2 em, .slide .tag em { font-style: italic; color: var(--gold2); }
.mega { font-family: var(--serif); font-size: clamp(3rem, 7vw, 5rem);
  letter-spacing: 0.16em; color: var(--gold2);
  text-transform: uppercase; }
.mega2 { font-family: var(--serif);
  font-size: clamp(2.2rem, 5vw, 3.6rem); }
.tag { font-family: var(--serif); font-size: 1.4rem; font-style: italic;
  margin: 18px 0; max-width: 720px; }
.mini { color: var(--dim2); font-size: 0.8rem; margin-top: 28px;
  max-width: 720px; }
.slide ul { padding-left: 22px; max-width: 780px; }
.slide li { color: var(--dim); margin-bottom: 12px; font-size: 1rem; }
.slide p { color: var(--dim); max-width: 780px; }
.tres { display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 22px; margin-top: 10px; }
.cx { background: var(--panel); border: 1px solid var(--line);
  border-radius: 4px; padding: 24px; }
.cx b { font-family: var(--serif); color: var(--gold);
  font-size: 1.4rem; }
.cx h3 { font-family: var(--serif); font-weight: 500;
  font-size: 1.25rem; margin: 8px 0; }
.cx p { font-size: 0.88rem; }
.duas-col { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
.duas-col h3 { font-family: var(--serif); font-weight: 500;
  margin-bottom: 10px; }
.ok { color: var(--green); } .nao { color: var(--gold); }
.pg { position: absolute; bottom: 3vh; right: 8vw;
  font-family: var(--serif); color: var(--gold); font-size: 0.85rem; }
.nav-deck { position: fixed; bottom: 3vh; left: 8vw; display: flex;
  gap: 10px; z-index: 5; }
.nav-deck button { background: var(--panel); color: var(--gold2);
  border: 1px solid var(--line2); padding: 8px 18px; cursor: pointer;
  font-family: var(--sans); letter-spacing: 0.12em; font-size: 0.7rem;
  text-transform: uppercase; border-radius: 2px; }
.nav-deck button:hover { border-color: var(--gold); }
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
<meta name="theme-color" content="#070b08">
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
