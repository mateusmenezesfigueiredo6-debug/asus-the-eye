// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
//
// Gate de acesso do site de apresentacao do vertical cannabis.
// Todo request sem cookie valido recebe a tela de codigo; o codigo e
// comparado em tempo constante contra o secret SITE_ACCESS_CODE e, se
// correto, emite cookie HMAC com validade. Nada do conteudo vaza sem o
// cookie — inclusive assets.

export interface Env {
  ASSETS: Fetcher;
  SITE_ACCESS_CODE: string;
  COOKIE_SECRET: string;
  // Automacoes (opcionais ate o deploy configurar):
  OPTOUT?: KVNamespace;
  DEST_EMAIL?: string; // caixa da associacao que recebe os pacotes
  FROM_EMAIL?: string; // remetente dos disparos (dominio proprio)
}

// Envia email via MailChannels (gratuito para Workers publicados).
async function enviarEmail(
  env: Env,
  para: string,
  assunto: string,
  corpo: string,
): Promise<boolean> {
  if (!env.FROM_EMAIL) return false;
  const r = await fetch("https://api.mailchannels.net/tx/v1/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: para }] }],
      from: { email: env.FROM_EMAIL, name: "Associacao Gota Verde" },
      subject: assunto,
      content: [{ type: "text/plain", value: corpo }],
    }),
  });
  return r.ok;
}

const TEMPLATE_MEDICO = (nome: string, crm: string, unsub: string) =>
  `Dr(a). ${nome},

Somos a Associacao Gota Verde, entidade de pacientes de cannabis
medicinal em formacao, com rastreabilidade auditavel (laudo por lote,
importacao assistida via RDC 660/2022 e farmacovigilancia ativa).
Estamos convidando medicos com CRM ativo (${crm}) para o corpo clinico.

Modelos de parceria: pagamento por consulta (valor definido pelo
proprio medico), hora clinica ou conselho cientifico. Nao trabalhamos
com remuneracao vinculada a prescricao - vedado pelo CEM e pela nossa
politica.

Teria 20 minutos esta semana para uma conversa?

Associacao Gota Verde
Para nao receber mais mensagens: ${unsub}`;

const TEMPLATE_EMPRESA = (nome: string, unsub: string) =>
  `Prezados, ${nome},

Somos a Associacao Gota Verde, entidade de pacientes de cannabis
medicinal em formacao. Buscamos parcerias com plataformas e empresas do
setor (telemedicina, laboratorios, fornecedores internacionais com
produto regularizado na origem) para a operacao de importacao assistida
via RDC 660/2022.

Podemos agendar uma conversa?

Associacao Gota Verde
Para nao receber mais mensagens: ${unsub}`;

const COOKIE = "gota_acesso";
const VALIDADE_S = 60 * 60 * 12; // 12 horas

function timingSafeEqual(a: string, b: string): boolean {
  const enc = new TextEncoder();
  const ba = enc.encode(a);
  const bb = enc.encode(b);
  if (ba.length !== bb.length) {
    // compara mesmo assim para nao vazar o tamanho pelo tempo
    let x = 1;
    for (let i = 0; i < ba.length; i++) x |= ba[i] ^ (bb[i % (bb.length || 1)] ?? 0);
    return x === 0 && false;
  }
  let diff = 0;
  for (let i = 0; i < ba.length; i++) diff |= ba[i] ^ bb[i];
  return diff === 0;
}

async function hmac(secret: string, msg: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function cookieValido(req: Request, env: Env): Promise<boolean> {
  const header = req.headers.get("Cookie") ?? "";
  const m = header.match(new RegExp(`${COOKIE}=([^;]+)`));
  if (!m) return false;
  const [exp, assinatura] = m[1].split(".");
  if (!exp || !assinatura) return false;
  const expNum = Number(exp);
  if (!Number.isFinite(expNum) || expNum < Date.now() / 1000) return false;
  const esperado = await hmac(env.COOKIE_SECRET, exp);
  return timingSafeEqual(assinatura, esperado);
}

function telaCodigo(erro: boolean): Response {
  const body = `<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Acesso restrito</title>
<style>
body{background:#070b08;color:#ede9dd;font-family:Georgia,serif;
display:flex;align-items:center;justify-content:center;min-height:100vh;
margin:0}
form{border:1px solid #1c2a1f;padding:48px;border-radius:4px;
text-align:center;background:#0f1811;max-width:360px}
h1{font-weight:normal;letter-spacing:.24em;color:#e6cf8e;
font-size:1.1rem;text-transform:uppercase}
p{color:#97a698;font-size:.85rem;margin:14px 0 22px}
input{background:#070b08;border:1px solid #2a3d2e;color:#ede9dd;
padding:12px;width:100%;text-align:center;letter-spacing:.4em;
font-size:1rem;border-radius:2px}
button{margin-top:16px;background:#c9a44a;border:0;color:#14100a;
padding:12px 30px;letter-spacing:.2em;text-transform:uppercase;
font-size:.7rem;cursor:pointer;border-radius:2px}
.erro{color:#d97676;font-size:.8rem;margin-top:12px}
</style></head><body>
<form method="POST" action="/acesso">
<h1>Gota Verde</h1>
<p>Material de apresentacao restrito.<br>Informe o codigo de acesso.</p>
<input type="password" name="codigo" autofocus autocomplete="off">
<button type="submit">Entrar</button>
${erro ? '<p class="erro">Codigo incorreto.</p>' : ""}
</form></body></html>`;
  return new Response(body, {
    status: erro ? 401 : 200,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);

    if (req.method === "POST" && url.pathname === "/acesso") {
      const form = await req.formData();
      const codigo = String(form.get("codigo") ?? "");
      if (!env.SITE_ACCESS_CODE || !timingSafeEqual(codigo, env.SITE_ACCESS_CODE)) {
        return telaCodigo(true);
      }
      const exp = String(Math.floor(Date.now() / 1000) + VALIDADE_S);
      const assinatura = await hmac(env.COOKIE_SECRET, exp);
      return new Response(null, {
        status: 303,
        headers: {
          Location: "/",
          "Set-Cookie":
            `${COOKIE}=${exp}.${assinatura}; Path=/; Max-Age=${VALIDADE_S}; ` +
            "HttpOnly; Secure; SameSite=Lax",
        },
      });
    }

    // Opt-out publico (chega pelo link do email, sem cookie).
    if (req.method === "GET" && url.pathname === "/api/unsubscribe") {
      const e = (url.searchParams.get("e") ?? "").toLowerCase().trim();
      if (e && env.OPTOUT) await env.OPTOUT.put(`optout:${e}`, "1");
      return new Response(
        "Descadastro registrado. Voce nao recebera mais mensagens.",
        { headers: { "Content-Type": "text/plain; charset=utf-8" } },
      );
    }

    if (!(await cookieValido(req, env))) {
      return telaCodigo(false);
    }

    // Disparo de convites (admin, atras do gate). Corpo JSON:
    // { destinatarios: [{nome,email,crm?,tipo:"medico"|"empresa"}] }
    if (req.method === "POST" && url.pathname === "/api/outreach") {
      const dados = (await req.json()) as {
        destinatarios?: {
          nome: string; email: string; crm?: string; tipo?: string;
        }[];
      };
      const lote = (dados.destinatarios ?? []).slice(0, 100);
      let enviados = 0;
      let suprimidos = 0;
      for (const d of lote) {
        const email = (d.email ?? "").toLowerCase().trim();
        if (!email.includes("@")) continue;
        if (env.OPTOUT && (await env.OPTOUT.get(`optout:${email}`))) {
          suprimidos++;
          continue;
        }
        const unsub = `${url.origin}/api/unsubscribe?e=${encodeURIComponent(email)}`;
        const corpo =
          d.tipo === "empresa"
            ? TEMPLATE_EMPRESA(d.nome, unsub)
            : TEMPLATE_MEDICO(d.nome, d.crm ?? "", unsub);
        const ok = await enviarEmail(
          env,
          email,
          "Convite - Associacao Gota Verde",
          corpo,
        );
        if (ok) enviados++;
      }
      return Response.json({
        enviados,
        suprimidos,
        total: lote.length,
        configurado: Boolean(env.FROM_EMAIL),
      });
    }

    // Pacote de autorizacao ANVISA: encaminha por email a associacao.
    // Nao armazena dados de saude no Worker (transito, nao retencao).
    if (req.method === "POST" && url.pathname === "/api/autorizacao") {
      const p = (await req.json()) as Record<string, string>;
      const corpo = `NOVO PACOTE DE AUTORIZACAO (RDC 660)

Paciente: ${p.nome ?? ""}
CPF: ${p.cpf ?? ""}
Data de nascimento: ${p.nascimento ?? ""}
Email: ${p.email ?? ""}
Telefone: ${p.telefone ?? ""}
Endereco: ${p.endereco ?? ""}

Medico: ${p.medico ?? ""} - CRM ${p.crm ?? ""}/${p.uf ?? ""}
Data da receita: ${p.dataReceita ?? ""}

Produto prescrito: ${p.produto ?? ""}
Concentracao/posologia: ${p.posologia ?? ""}
Fornecedor pretendido: ${p.fornecedor ?? ""}

Proximo passo: despachante conduz o cadastro no Gov.br como
representante (procuracao assinada) e retorna ao paciente com o
protocolo.`;
      const ok = env.DEST_EMAIL
        ? await enviarEmail(
            env,
            env.DEST_EMAIL,
            `Pacote de autorizacao - ${p.nome ?? "paciente"}`,
            corpo,
          )
        : false;
      return Response.json({ recebido: true, encaminhado: ok });
    }

    return env.ASSETS.fetch(req);
  },
};
