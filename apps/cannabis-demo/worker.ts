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
}

const COOKIE = "cinala_acesso";
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
<h1>Cinala Verde</h1>
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

    if (!(await cookieValido(req, env))) {
      return telaCodigo(false);
    }
    return env.ASSETS.fetch(req);
  },
};
