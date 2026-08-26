/**
 * the-eye-leads — endpoint de captura dos fronts Ledger e Markets.
 *
 * POST /api/lead            público (CORS restrito) — grava {email, product, source}
 * GET  /api/leads?product=  privado (Bearer LEADS_TOKEN) — lista leads
 * GET  /api/health          público — ok
 *
 * Desenho fail-closed, no padrão do public-verifier: o caminho público só
 * INSERE; leitura exige segredo. Rate limit por IP em D1 (30/h) porque o
 * plano free não tem Durable Objects — contenção aqui é aceitável: lead é
 * tráfego baixo e o custo de um estouro é um insert a mais, não corrupção.
 */

export interface Env {
  DB: D1Database;
  LEADS_TOKEN: string;
  /** Origens permitidas, separadas por vírgula. Vazio = mesmo-origem apenas. */
  ALLOWED_ORIGINS?: string;
}

const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,24}$/;
const PRODUCTS = new Set(["ledger", "markets"]);
const RATE_LIMIT = 30; // envios por IP por hora

function corsHeaders(origin: string | null, env: Env): Record<string, string> {
  const allowed = (env.ALLOWED_ORIGINS ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  const h: Record<string, string> = {
    "access-control-allow-methods": "POST, GET, OPTIONS",
    "access-control-allow-headers": "content-type, authorization",
    "access-control-max-age": "86400",
  };
  if (origin && allowed.includes(origin)) h["access-control-allow-origin"] = origin;
  return h;
}

function json(body: unknown, status: number, extra: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...extra },
  });
}

async function rateLimited(env: Env, ip: string): Promise<boolean> {
  const window = new Date().toISOString().slice(0, 13); // hora corrente
  const row = await env.DB.prepare(
    `INSERT INTO rate (ip, window_start, hits) VALUES (?1, ?2, 1)
     ON CONFLICT (ip, window_start) DO UPDATE SET hits = hits + 1
     RETURNING hits`,
  ).bind(ip, window).first<{ hits: number }>();
  return (row?.hits ?? 0) > RATE_LIMIT;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const origin = request.headers.get("origin");
    const cors = corsHeaders(origin, env);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

    if (url.pathname === "/api/health") return json({ ok: true }, 200, cors);

    if (url.pathname === "/api/lead" && request.method === "POST") {
      const ip = request.headers.get("cf-connecting-ip") ?? "unknown";
      if (await rateLimited(env, ip)) return json({ error: "too many requests" }, 429, cors);

      let body: { email?: string; product?: string; source?: string };
      try {
        body = await request.json();
      } catch {
        return json({ error: "invalid json" }, 400, cors);
      }

      const email = (body.email ?? "").trim().toLowerCase();
      const product = (body.product ?? "").trim().toLowerCase();
      const source = (body.source ?? "unknown").trim().slice(0, 64);

      if (!EMAIL_RE.test(email)) return json({ error: "invalid email" }, 400, cors);
      if (!PRODUCTS.has(product)) return json({ error: "invalid product" }, 400, cors);

      await env.DB.prepare(
        "INSERT INTO leads (email, product, source) VALUES (?1, ?2, ?3)",
      ).bind(email, product, source).run();

      return json({ ok: true }, 201, cors);
    }

    if (url.pathname === "/api/leads" && request.method === "GET") {
      const auth = request.headers.get("authorization") ?? "";
      if (auth !== `Bearer ${env.LEADS_TOKEN}`) return json({ error: "unauthorized" }, 401, cors);

      const product = url.searchParams.get("product");
      const stmt = product && PRODUCTS.has(product)
        ? env.DB.prepare(
            "SELECT id, email, product, source, created_at FROM leads WHERE product = ?1 ORDER BY created_at DESC LIMIT 500",
          ).bind(product)
        : env.DB.prepare(
            "SELECT id, email, product, source, created_at FROM leads ORDER BY created_at DESC LIMIT 500",
          );
      const { results } = await stmt.all();
      return json({ count: results.length, leads: results }, 200, cors);
    }

    return json({ error: "not found" }, 404, cors);
  },
} satisfies ExportedHandler<Env>;
