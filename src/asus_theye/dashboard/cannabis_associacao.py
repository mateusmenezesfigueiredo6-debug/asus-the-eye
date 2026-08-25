# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Site institucional da associacao de pacientes de cannabis medicinal.

Este modulo gera, como funcoes puras, as paginas do site da associacao
de pacientes (nome provisorio: Associacao Gota Verde — o nome definitivo
sera deliberado na assembleia de fundacao). E um site separado do site
da empresa (cannabis_demo.py): a associacao nao vende, nao estoca e nao
intermedia pagamento de produto; ela representa o paciente perante a
ANVISA, orienta receita e importacao (RDC 660/2022), rateia custos
administrativos sem lucro e defende o acesso.

Tudo aqui obedece a regra de honestidade do projeto: fase em fundacao,
nenhum cultivo existe hoje, prazos judiciais sao faixas tipicas e nada
substitui consulta medica ou advogado.
"""

from __future__ import annotations

BRAND = "Associacao Gota Verde"
BRAND_TAG = "associacao de pacientes de cannabis medicinal"
NOTA_NOME = "Nome provisorio: o nome definitivo da associacao sera deliberado e aprovado na assembleia de fundacao."

FONTES = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    "family=Lora:ital,wght@0,400;0,500;0,600;1,400&"
    'family=Inter:wght@400;500;600&display=swap" rel="stylesheet">'
)

# Identidade da associacao: mesma familia clara do site da empresa, mas
# mais acolhedora e institucional — fundo palha, verde musgo como acento,
# terra como secundario, cantos arredondados 6px, serifa Lora.
CSS_BASE = """
:root {
  --bg: #f7f6f1; --panel: #ffffff; --line: #e2ddd0;
  --ink: #232821; --dim: #4e564b; --dim2: #8b9083;
  --verde: #4a6b52; --verde2: #3a5641; --terra: #8a6f4d;
  --serif: 'Lora', Georgia, 'Times New Roman', serif;
  --sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body { background: var(--bg); color: var(--ink);
  font-family: var(--sans); font-weight: 400;
  line-height: 1.75; letter-spacing: 0.005em; }
a { color: var(--verde); text-decoration: none;
  transition: color 0.2s ease; }
a:hover { color: var(--verde2); text-decoration: underline;
  text-underline-offset: 3px; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 0 30px; }
header.site { padding: 30px 0 26px; display: flex; align-items: center;
  justify-content: space-between; gap: 26px; flex-wrap: wrap;
  border-bottom: 1px solid var(--line); }
.logo { font-family: var(--serif); font-size: 1.35rem;
  letter-spacing: 0.01em; color: var(--ink); font-weight: 500; }
.logo small { display: block; font-family: var(--sans);
  font-size: 0.6rem; letter-spacing: 0.24em; color: var(--terra);
  text-transform: uppercase; margin-top: 3px; font-weight: 500; }
nav.menu { display: flex; gap: 22px; font-size: 0.68rem;
  letter-spacing: 0.16em; text-transform: uppercase; font-weight: 500;
  flex-wrap: wrap; }
nav.menu a { color: var(--dim2); padding-bottom: 5px;
  border-bottom: 1px solid transparent; }
nav.menu a:hover { color: var(--verde); text-decoration: none; }
nav.menu a.on { color: var(--verde);
  border-bottom-color: var(--verde); }
.hero { padding: 88px 0 64px; }
.hero .kicker, .kicker { font-size: 0.64rem; letter-spacing: 0.28em;
  text-transform: uppercase; color: var(--terra); font-weight: 600; }
.hero h1 { font-family: var(--serif); font-size: clamp(2.2rem, 4.8vw,
  3.6rem); font-weight: 500; line-height: 1.12; max-width: 820px;
  margin-top: 20px; letter-spacing: -0.01em; }
.hero h1 em { font-style: italic; color: var(--verde); }
.hero p.lede { color: var(--dim); max-width: 620px; margin-top: 24px;
  font-size: 1.03rem; }
.nota-nome { display: inline-block; margin-top: 18px; font-size:
  0.78rem; color: var(--dim2); border: 1px dashed var(--line);
  border-radius: 6px; padding: 8px 14px; background: var(--panel); }
.cta-row { margin-top: 36px; display: flex; gap: 14px; flex-wrap: wrap; }
.btn { display: inline-block; padding: 13px 28px; border-radius: 6px;
  font-size: 0.68rem; letter-spacing: 0.18em; text-transform: uppercase;
  font-weight: 600; }
.btn.solid { background: var(--verde); color: #ffffff; }
.btn.solid:hover { background: var(--verde2); color: #ffffff;
  text-decoration: none; }
.btn.ghost { border: 1px solid var(--ink); color: var(--ink); }
.btn.ghost:hover { border-color: var(--verde); color: var(--verde);
  text-decoration: none; }
.badge-fase { display: inline-block; border: 1px solid var(--terra);
  color: var(--terra); background: var(--panel); font-size: 0.6rem;
  letter-spacing: 0.2em; text-transform: uppercase; padding: 6px 15px;
  margin-bottom: 26px; font-weight: 600; border-radius: 6px; }
section.bloco { border-top: 1px solid var(--line); padding: 72px 0; }
section.bloco .num { font-family: var(--serif); font-size: 0.9rem;
  color: var(--terra); letter-spacing: 0.28em; }
section.bloco h2 { font-family: var(--serif); font-weight: 500;
  font-size: clamp(1.7rem, 3vw, 2.4rem); margin: 12px 0 22px;
  letter-spacing: -0.01em; }
section.bloco h3 { font-family: var(--serif); font-weight: 500;
  font-size: 1.25rem; margin: 18px 0 8px; }
section.bloco p, section.bloco li { color: var(--dim); max-width: 720px;
  font-size: 0.95rem; }
section.bloco ul { padding-left: 22px; margin-top: 10px; }
section.bloco li { margin-bottom: 10px; }
section.bloco b { color: var(--ink); font-weight: 600; }
.duas { display: grid; grid-template-columns: repeat(auto-fit,
  minmax(300px, 1fr)); gap: 28px; }
.painel { background: var(--panel); border: 1px solid var(--line);
  border-radius: 6px; padding: 28px; }
.painel.faz { border-top: 3px solid var(--verde); }
.painel.naofaz { border-top: 3px solid var(--terra); }
.painel h3 { margin-top: 0; }
table.tab { border-collapse: collapse; width: 100%; margin-top: 24px;
  font-size: 0.88rem; background: var(--panel);
  border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
table.tab th, table.tab td { border: 1px solid var(--line);
  padding: 13px 15px; text-align: left; color: var(--dim);
  vertical-align: top; }
table.tab th { color: var(--ink); background: var(--bg);
  font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;
  font-size: 0.62rem; }
.pipeline { counter-reset: fase; margin-top: 26px; }
.pipeline .fase { display: flex; gap: 24px; padding: 24px 0;
  border-top: 1px solid var(--line); }
.pipeline .fase::before { counter-increment: fase;
  content: counter(fase, decimal-leading-zero);
  font-family: var(--serif); font-size: 1.4rem; color: var(--terra);
  min-width: 52px; }
.pipeline h4 { font-family: var(--serif); font-size: 1.2rem;
  font-weight: 500; }
.pipeline p { font-size: 0.9rem; }
footer.site { border-top: 1px solid var(--line); padding: 36px 0 64px;
  color: var(--dim2); font-size: 0.78rem; }
.form-medico { max-width: 740px; margin-top: 28px; }
.form-medico .campo-linha { display: grid; grid-template-columns:
  repeat(auto-fit, minmax(200px, 1fr)); gap: 18px; margin-bottom: 18px; }
.form-medico label { display: block; font-size: 0.64rem;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--dim);
  font-weight: 600; }
.form-medico input, .form-medico select { display: block; width: 100%;
  margin-top: 8px; background: var(--panel); border: 1px solid
  var(--line); color: var(--ink); padding: 12px 13px; border-radius: 6px;
  font-family: var(--sans); font-size: 0.95rem; }
.form-medico input:focus, .form-medico select:focus { outline: none;
  border-color: var(--verde); }
.form-medico .check { display: flex; gap: 10px; align-items:
  flex-start; text-transform: none; letter-spacing: normal;
  font-size: 0.86rem; margin: 18px 0; color: var(--dim);
  font-weight: 400; }
.form-medico .check input { width: auto; margin-top: 4px;
  accent-color: var(--verde); }
.form-medico button { cursor: pointer; border: 0; font-family:
  var(--sans); }
.form-medico .btn.ghost { border: 1px solid var(--ink);
  background: transparent; }
.crm-status { font-size: 0.86rem; min-height: 1.4em; margin: 4px 0; }
.crm-status.ok { color: var(--verde); }
.crm-status.erro { color: #a33b3b; }
.mini-form { font-size: 0.78rem; color: var(--dim2); }
.aviso { background: var(--panel); border: 1px solid var(--line);
  border-left: 3px solid var(--verde); border-radius: 6px;
  padding: 18px 22px; margin: 30px 0; color: var(--dim);
  font-size: 0.88rem; max-width: 740px; }
.aviso.alerta { border-left-color: var(--terra); }
"""

PAGINAS = (
    ("index.html", "Quem somos"),
    ("como_funciona.html", "Como funciona"),
    ("autorizacao.html", "Autorizacao"),
    ("associe_se.html", "Associe-se"),
    ("transparencia.html", "Transparencia"),
    ("cultivo.html", "Cultivo"),
    ("contato.html", "Contato"),
)

RODAPE = (
    f"<p>{BRAND} — associacao de pacientes em processo de fundacao. "
    "Este site e material demonstrativo. A associacao nao vende produtos, "
    "nao estoca e nao intermedia pagamento de produto: produtos a base de "
    "cannabis exigem prescricao medica e via legal de acesso (RDC "
    "660/2022 ou produto autorizado pela ANVISA). Nada aqui substitui "
    "consulta medica ou orientacao de advogado(a).</p>"
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
<meta name="description" content="{BRAND}: {BRAND_TAG}. Representacao
do paciente na ANVISA, orientacao de receita e importacao (RDC
660/2022) e rateio de custos sem lucro. Em fundacao.">
<meta property="og:title" content="{titulo} — {BRAND}">
<meta property="og:description" content="{BRAND_TAG}">
<meta property="og:type" content="website">
<meta property="og:image" content="icone.svg">
{FONTES}
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icone.svg" type="image/svg+xml">
<meta name="theme-color" content="#f7f6f1">
<style>{CSS_BASE}</style>
</head>
<body>
<div class="wrap">
<header class="site">
  <span class="logo">{BRAND}<small>{BRAND_TAG}</small></span>
  <nav class="menu">{nav}</nav>
</header>
{corpo}
<footer class="site">
  {RODAPE}
  <p style="margin-top:10px">{NOTA_NOME}</p>
</footer>
</div>
</body>
</html>"""


def index_page() -> str:
    corpo = f"""
<section class="hero">
  <span class="badge-fase">Fase atual: em fundacao</span>
  <h1>Uma associacao de pacientes, feita <em>pelos pacientes</em>.</h1>
  <p class="lede">A {BRAND} esta sendo fundada para fazer o que o
  paciente de cannabis medicinal nao deveria ter de fazer sozinho:
  entender a regra, montar o pedido, falar com a ANVISA e trazer o
  tratamento para casa pela via legal — com contabilidade aberta e sem
  fins lucrativos.</p>
  <span class="nota-nome">{NOTA_NOME}</span>
  <div class="cta-row">
    <a class="btn solid" href="associe_se.html">Quero me associar</a>
    <a class="btn ghost" href="como_funciona.html">Como funciona</a>
    <a class="btn ghost" href="autorizacao.html">Pedir autorizacao</a>
  </div>
</section>
<section class="bloco">
  <span class="num">01</span>
  <h2>O que a associacao faz — e o que ela nao faz</h2>
  <div class="duas">
    <div class="painel faz">
      <h3>O que a associacao FAZ</h3>
      <ul>
        <li><b>Representa o paciente na ANVISA</b>, por procuracao, no
        pedido de autorizacao de importacao (RDC 660/2022).</li>
        <li><b>Orienta receita e importacao</b>: qual documento falta,
        como o medico deve prescrever, qual fornecedor aceita o
        rito.</li>
        <li><b>Rateia custos administrativos</b> entre associados, sem
        lucro e com contabilidade aberta.</li>
        <li><b>Defende o acesso</b>: juridica e institucionalmente, do
        caso individual a politica publica.</li>
      </ul>
    </div>
    <div class="painel naofaz">
      <h3>O que ela NAO faz</h3>
      <ul>
        <li><b>Nao vende</b> produto de cannabis, de nenhum tipo.</li>
        <li><b>Nao estoca</b> nem armazena produto de terceiros.</li>
        <li><b>Nao intermedia pagamento de produto</b>: o pagamento vai
        sempre do paciente direto ao fornecedor.</li>
        <li><b>Nao promete cura</b>: indicacao terapeutica e conversa
        entre o paciente e o medico prescritor.</li>
      </ul>
    </div>
  </div>
  <div class="aviso">Fase atual: em fundacao. Estatuto e edital de
  assembleia em preparacao; ainda nao ha CNPJ nem operacao. Deixe seu
  contato em <a href="associe_se.html">Associe-se</a> para ser
  convidado(a) a assembleia de fundacao.</div>
</section>
<section class="bloco">
  <span class="num">02</span>
  <h2>Por que uma associacao</h2>
  <p>A via legal de acesso ja existe: desde 2015 a ANVISA autoriza a
  importacao por pessoa fisica, e a RDC 660/2022 simplificou o rito. O
  que falta ao paciente e estrutura: alguem que conheca o processo,
  confira a papelada e acompanhe o pedido ate o produto chegar. Uma
  associacao sem fins lucrativos faz isso com custo rateado — e
  constroi, pedido a pedido, o historico documentado que sustenta os
  proximos passos do acesso, inclusive o pedido judicial de cultivo
  (veja <a href="cultivo.html">Cultivo</a>).</p>
</section>"""
    return _shell("Quem somos", "index.html", corpo)


def como_funciona_page() -> str:
    corpo = """
<section class="hero">
  <span class="badge-fase">Rota RDC 660/2022</span>
  <h1>Do consultorio ate a sua casa, <em>em seis passos</em></h1>
  <p class="lede">A importacao por paciente e a via legal em vigor. O
  caminho abaixo e o que a associacao acompanha com voce, do inicio ao
  fim.</p>
</section>
<section class="bloco">
  <div class="pipeline">
    <div class="fase"><div><h4>Consulta medica</h4>
      <p>Um(a) medico(a) com CRM ativo avalia o seu caso. A associacao
      nao prescreve e nao indica tratamento: sem avaliacao medica, nada
      comeca.</p></div></div>
    <div class="fase"><div><h4>Receita</h4>
      <p>A prescricao precisa nomear o produto, a concentracao e a
      posologia. Orientamos o que a receita deve conter para o pedido
      nao voltar.</p></div></div>
    <div class="fase"><div><h4>Autorizacao no Gov.br</h4>
      <p>O pedido e protocolado no Gov.br em nome do paciente — nos
      casos limpos (documentacao completa e legivel), a autorizacao sai
      em minutos e vale 2 anos. A associacao conduz o cadastro como sua
      representante, por procuracao.</p></div></div>
    <div class="fase"><div><h4>Compra direta do fornecedor</h4>
      <p>Com a autorizacao em maos, o paciente compra direto do
      fornecedor no exterior. O pagamento do produto vai SEMPRE do
      paciente ao fornecedor: a associacao nao recebe, nao repassa e nao
      intermedia esse dinheiro.</p></div></div>
    <div class="fase"><div><h4>Courier e ANVISA</h4>
      <p>O produto viaja por courier e passa pela conferencia da ANVISA
      na entrada, vinculada a sua autorizacao.</p></div></div>
    <div class="fase"><div><h4>Chegada em casa</h4>
      <p>O produto chega ao seu endereco. A associacao acompanha prazos,
      lembra a renovacao da autorizacao e registra o historico do seu
      acesso.</p></div></div>
  </div>
  <div class="aviso alerta">Aviso importante: o pagamento do produto e
  sempre uma transacao direta entre o paciente e o fornecedor. A
  associacao rateia apenas custos administrativos proprios (cartorio,
  contabilidade, plataforma), definidos em assembleia e prestados em
  contas abertas.</div>
</section>"""
    return _shell("Como funciona", "como_funciona.html", corpo)


def autorizacao_page() -> str:
    """Wizard do associado: mesmo comportamento do wizard da empresa.

    Coleta e formata o pedido, envia o pacote a equipe (endpoint
    /api/autorizacao) e gera a versao para impressao; a submissao final
    no Gov.br e feita por representante humano com a procuracao.
    """
    corpo = """
<section class="hero">
  <span class="badge-fase">Importacao assistida — RDC 660/2022</span>
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


def associe_se_page() -> str:
    corpo = """
<section class="hero">
  <span class="badge-fase">Em fundacao — lista de interesse</span>
  <h1>Associe-se e ajude a <em>fundar</em></h1>
  <p class="lede">A associacao esta em formacao. Quem se inscrever agora
  entra na lista de interesse e sera convidado(a) a assembleia de
  fundacao, onde o nome, o estatuto e os valores de anuidade serao
  decididos em conjunto.</p>
</section>
<section class="bloco">
  <form id="form-associado" class="form-medico">
    <div class="campo-linha">
      <label>Nome completo
        <input type="text" name="nome" required autocomplete="name">
      </label>
      <label>Email
        <input type="email" name="email" required autocomplete="email">
      </label>
    </div>
    <div class="campo-linha">
      <label>Telefone
        <input type="tel" name="telefone" required autocomplete="tel">
      </label>
      <label>Cidade / UF
        <input type="text" name="cidade" required
          placeholder="ex.: Salvador / BA">
      </label>
    </div>
    <div class="campo-linha">
      <label>Condicao de saude (opcional)
        <input type="text" name="condicao"
          placeholder="informe se quiser">
      </label>
      <label>Ja possui receita medica?
        <select name="receita" required>
          <option value="">Selecione</option>
          <option>Sim</option>
          <option>Nao</option>
        </select>
      </label>
    </div>
    <p>
      <button type="submit" class="btn solid">Entrar na lista de
      interesse</button>
    </p>
    <p class="crm-status" id="assoc-status"></p>
    <p class="mini-form">O envio abre seu email com os dados preenchidos
    (nao armazenamos nada neste site). A condicao de saude e opcional e,
    se informada, sera tratada como dado sensivel nos termos da
    LGPD.</p>
  </form>
  <div class="aviso">Anuidade e rateio: os valores de anuidade e a regra
  de rateio dos custos administrativos serao definidos na assembleia de
  fundacao, votados pelos proprios associados e publicados na pagina de
  <a href="transparencia.html">Transparencia</a>.</div>
</section>
<script>
(function () {
  var form = document.getElementById('form-associado');
  var status = document.getElementById('assoc-status');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var corpo = 'Nome: ' + form.nome.value
      + '%0AEmail: ' + form.email.value
      + '%0ATelefone: ' + form.telefone.value
      + '%0ACidade/UF: ' + form.cidade.value
      + '%0ACondicao de saude (opcional): '
      + (form.condicao.value || 'nao informada')
      + '%0APossui receita medica: ' + form.receita.value;
    status.className = 'crm-status ok';
    status.textContent = 'Abrindo seu email com os dados preenchidos...';
    location.href = 'mailto:associados@example.invalid'
      + '?subject=' + encodeURIComponent(
        'Lista de interesse - assembleia de fundacao')
      + '&body=' + corpo;
  });
})();
</script>"""
    return _shell("Associe-se", "associe_se.html", corpo)


def transparencia_page() -> str:
    docs = (
        ("Estatuto Social", "Objeto, orgaos, direitos e deveres dos associados"),
        ("Ata de Assembleia de Fundacao", "Deliberacoes, nome definitivo, diretoria eleita"),
        ("Edital de Convocacao", "Convocacao publica da assembleia de fundacao"),
        ("Lista de Presenca", "Fundadores presentes na assembleia"),
        ("Termos de Posse da Diretoria", "Posse dos dirigentes eleitos"),
    )
    linhas = "".join(
        f"<tr><td>{nome}</td><td>{desc}</td><td>Disponivel no repositorio / apos registro em cartorio</td></tr>"
        for nome, desc in docs
    )
    corpo = f"""
<section class="hero">
  <span class="badge-fase">Contas abertas, sempre</span>
  <h1>Transparencia nao e promessa: <em>e regra estatutaria</em></h1>
  <p class="lede">Uma associacao de pacientes vive de confianca. Aqui
  ficarao publicados o estatuto, as atas e a prestacao de contas — e a
  contabilidade sera aberta a todos os associados, com rateio de custos
  sem lucro.</p>
</section>
<section class="bloco">
  <span class="num">01</span>
  <h2>Documentos de fundacao</h2>
  <table class="tab">
    <tr><th>Documento</th><th>Conteudo</th><th>Situacao</th></tr>
    {linhas}
  </table>
</section>
<section class="bloco">
  <span class="num">02</span>
  <h2>Regras de contas</h2>
  <ul>
    <li><b>Contabilidade aberta aos associados.</b> Qualquer associado
    pode consultar receitas, despesas e o rateio, a qualquer tempo.</li>
    <li><b>Rateio de custos sem lucro.</b> A associacao cobre apenas os
    seus custos administrativos, divididos entre os associados conforme
    regra aprovada em assembleia. Nao ha margem, comissao ou repasse
    comercial.</li>
    <li><b>Prestacao de contas periodica</b>, apresentada em assembleia
    e publicada nesta pagina.</li>
  </ul>
</section>"""
    return _shell("Transparencia", "transparencia.html", corpo)


def cultivo_page() -> str:
    corpo = """
<section class="hero">
  <span class="badge-fase">Fase judicial — planejamento</span>
  <h1>Cultivo: o caminho e <em>judicial</em>, e ainda nao comecou</h1>
  <p class="lede">Sejamos exatos: a associacao NAO cultiva hoje, e nenhum
  cultivo comecara sem autorizacao judicial expressa. Esta pagina
  explica, com honestidade, as duas vias em estudo e onde cada uma esta.</p>
</section>
<section class="bloco">
  <span class="num">01</span>
  <h2>Habeas corpus preventivo (salvo-conduto)</h2>
  <p>O habeas corpus preventivo (CF, art. 5, LXVIII; CPP, art. 660,
  par. 4) pede ao juiz um salvo-conduto: uma ordem que proibe prisao e
  processo contra pessoas nomeadas por cultivarem cannabis
  exclusivamente para fim terapeutico, nos limites exatos da decisao.
  Nao e licenca sanitaria, nao e autorizacao da ANVISA e nao cria
  direito de vender. O STJ ja concedeu salvo-condutos a pacientes
  (RHC 123.402/RS, 2021) e ha precedentes estendidos a associacoes —
  mas nao ha tese vinculante: cada decisao vale nos seus termos.</p>
  <h3>O que o juiz examina</h3>
  <ul>
    <li>Necessidade terapeutica comprovada: pacientes reais, laudos e
    prescricoes de medico com CRM ativo.</li>
    <li>Via legal previa esgotada ou inviavel: autorizacoes RDC 660 em
    nome dos pacientes e custo de importacao insustentavel.</li>
    <li>Associacao idonea: estatuto, atas, diretoria formalizada.</li>
    <li>Protocolo tecnico: responsavel tecnico, local unico, controle de
    acesso, analise de teor e rastreabilidade.</li>
    <li>Zero comercio: apenas rateio de custo com contabilidade
    aberta.</li>
  </ul>
  <h3>Prazos tipicos (faixas, nao promessas)</h3>
  <ul>
    <li>Preparacao do dossie: 1 a 3 meses.</li>
    <li>Liminar: de dias a poucas semanas apos a impetracao — sem
    liminar, o cultivo nao pode comecar.</li>
    <li>Sentenca de merito: 6 a 18 meses; com recursos, o processo
    completo pode levar 2 a 4 anos (a liminar, enquanto vigente, ja
    protege).</li>
  </ul>
</section>
<section class="bloco">
  <span class="num">02</span>
  <h2>Sandbox regulatorio da ANVISA (RDC 1.014/2026)</h2>
  <p>A RDC 1.014/2026 criou um sandbox regulatorio EXCLUSIVO para
  associacoes de pacientes sem fins lucrativos: ambiente experimental de
  ate 5 anos, sob supervisao direta da ANVISA, sem comercializacao. O
  requisito de corte, porem, e ter pessoa juridica constituida ha no
  minimo 2 anos na data da publicacao da RDC — o que uma associacao
  fundada agora nao alcanca neste primeiro ciclo. A entrada depende de
  edital de chamamento publico, ainda nao publicado ate 25/08/2026.
  Monitoraremos cada edital: um segundo ciclo pode ter corte diferente,
  e a associacao nasce ja com a documentacao no formato exigido.</p>
</section>
<section class="bloco">
  <span class="num">03</span>
  <h2>Roadmap honesto</h2>
  <div class="pipeline">
    <div class="fase"><div><h4>Fundacao</h4>
      <p>Assembleia, estatuto, cartorio e CNPJ. Nada de cultivo nesta
      fase.</p></div></div>
    <div class="fase"><div><h4>Operacao RDC 660 (6 a 12 meses)</h4>
      <p>Importacoes assistidas, prestacao de contas e historico
      documentado — e esse historico que demonstra necessidade
      terapeutica e boa-fe perante o Judiciario.</p></div></div>
    <div class="fase"><div><h4>Habeas corpus preventivo</h4>
      <p>Com o dossie maduro, advogado(a) habilitado(a) impetra o HC com
      pedido de liminar. So depois de decisao judicial favoravel, e nos
      seus limites exatos, um cultivo pode comecar.</p></div></div>
  </div>
  <div class="aviso alerta">Disclaimer: nao existe cultivo hoje e nenhum
  comecara sem autorizacao judicial. Esta pagina e orientacao interna de
  planejamento, nao parecer juridico; a peticao sera redigida e assinada
  por advogado(a) inscrito(a) na OAB. Prazos sao faixas tipicas
  observadas, nao promessas.</div>
</section>"""
    return _shell("Cultivo", "cultivo.html", corpo)


def contato_page() -> str:
    corpo = """
<section class="hero">
  <h1>Contato</h1>
  <p class="lede">Para associados, pacientes interessados, medicos,
  imprensa e parceiros institucionais:</p>
</section>
<section class="bloco">
  <ul>
    <li>Geral: <a href="mailto:contato@example.invalid">
    contato@example.invalid</a></li>
    <li>Associados: <a href="mailto:associados@example.invalid">
    associados@example.invalid</a></li>
    <li>Juridico: <a href="mailto:juridico@example.invalid">
    juridico@example.invalid</a></li>
  </ul>
  <div class="aviso">Enderecos de email sao provisorios (dominio
  example.invalid) ate a assembleia de fundacao definir o nome da
  associacao e o dominio definitivo ser contratado.</div>
</section>"""
    return _shell("Contato", "contato.html", corpo)


def manifest_webmanifest() -> str:
    return """{
  "name": "Associacao Gota Verde",
  "short_name": "Associacao",
  "start_url": "index.html",
  "display": "standalone",
  "background_color": "#f7f6f1",
  "theme_color": "#f7f6f1",
  "icons": [
    { "src": "icone.svg", "sizes": "any", "type": "image/svg+xml",
      "purpose": "any" }
  ]
}"""


def icone_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="24" fill="#f7f6f1"/>
  <circle cx="64" cy="64" r="56" fill="none" stroke="#e2ddd0"
    stroke-width="2"/>
  <circle cx="64" cy="64" r="40" fill="#4a6b52"/>
  <path d="M64 40c8 10 14 18 14 27a14 14 0 0 1-28 0c0-9 6-17 14-27z"
    fill="#f7f6f1"/>
  <circle cx="64" cy="70" r="5" fill="#8a6f4d"/>
</svg>"""


def exportar(destino: str = "dist-associacao") -> dict:
    """Escreve o site completo em `destino` e devolve o que foi gerado."""
    import pathlib

    raiz = pathlib.Path(destino)
    raiz.mkdir(parents=True, exist_ok=True)
    arquivos = {
        "index.html": index_page(),
        "como_funciona.html": como_funciona_page(),
        "autorizacao.html": autorizacao_page(),
        "associe_se.html": associe_se_page(),
        "transparencia.html": transparencia_page(),
        "cultivo.html": cultivo_page(),
        "contato.html": contato_page(),
        "manifest.webmanifest": manifest_webmanifest(),
        "icone.svg": icone_svg(),
    }
    for nome, conteudo in arquivos.items():
        (raiz / nome).write_text(conteudo, encoding="utf-8")
    return {"gerados": sorted(arquivos)}


if __name__ == "__main__":
    import sys

    alvo = sys.argv[1] if len(sys.argv) > 1 else "dist-associacao"
    print(exportar(alvo))
