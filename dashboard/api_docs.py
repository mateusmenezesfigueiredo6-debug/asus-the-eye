# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Painel do dashboard: documentação pública da API do verificador."""

from __future__ import annotations

from typing import Any

from .navegacao import CSS_NAV, barra


def api_docs_page() -> str:
    """Renderiza a documentação pública do verificador como HTML puro."""
    verify_curl_payload = """{
  "kind":"proof",
  "event_hash_sha256":"277c1efc72ea1fc36d7cb158eda95dd50ff6cdc0ef9c9af6fe77c2dbab4b7fdc",
  "proof":{
    "leaf":"ec84cf04e785ed45654796264b4b1a308ef81c664822804c481c4e9e8a782cdb",
    "siblings":[
      "2afea4b79d1dd4107d252f76e0cf4939214c70a868f1ed27dcf96071963f6c8c",
      "c8f83ff4af3055e208d57723416d5ca6fdfea0cfc8f535014a4ff19554cc2422"
    ],
    "root":"d48851a5bbfe8101261ceb6399ca36f320325f2db119e89a0dfa1111752edca4",
    "proof_format_version":"1"
  },
  "manifest_hash_valid":true
}"""
    verify_real_response = """{
  "valido":true,
  "motivo":"1 evento(s) íntegro(s) desde a gênese; âncora não fornecida",
  "estado":"nao_ancorado",
  "verificacoes":{"event_chain":true}
}"""
    root_real_response = """{
  "encontrada":true,
  "roots":[
    {
      "merkle_root":"1111111111111111111111111111111111111111111111111111111111111111",
      "manifest_hash_sha256":"2222222222222222222222222222222222222222222222222222222222222222",
      "tx_hash":"3333333333333333333333333333333333333333333333333333333333333333",
      "block_hash":"4444444444444444444444444444444444444444444444444444444444444444"
    }
  ]
}"""
    corpo = """
<section class="card">
  <h2>GET /health</h2>
  <p>Liveness anônimo do serviço.</p>
  <pre><code>curl -sS https://SEU_DOMINIO/health</code></pre>
  <h3>Corpo</h3>
  <pre><code>sem corpo</code></pre>
  <h3>Resposta real</h3>
  <pre><code>{"status":"ok"}</code></pre>
  <h3>O que NÃO faz</h3>
  <p>Não valida documentos, não consulta mercados e não expõe dados internos.</p>
</section>

<section class="card">
  <h2>POST /verify</h2>
  <p>Verifica localmente evento, corrente/histórico ou prova Merkle.</p>
  <p>Limite de 1 MiB por documento; nada é persistido.</p>
  <pre><code>curl -sS -X POST https://SEU_DOMINIO/verify \\
  -H 'content-type: application/json' \\
  -d '{verify_curl_payload}'</code></pre>
  <h3>Corpo</h3>
  <pre><code>{"kind":"event|chain|history|proof", "...":"documento de auditoria JSON"}</code></pre>
  <h3>Resposta real</h3>
  <pre><code>{verify_real_response}</code></pre>
  <h3>O que NÃO faz</h3>
  <p>Não grava payload, não repete conteúdo enviado e não afirma verdade material do documento.</p>
</section>

<section class="card">
  <h2>GET /root/AAAA-MM-DD</h2>
  <p>Retorna a raiz Merkle ancorada do dia (somente hashes).</p>
  <p>Quando há registro confirmado: HTTP 200 com <code>encontrada:true</code>.</p>
  <pre><code>curl -sS https://SEU_DOMINIO/root/2026-08-08</code></pre>
  <h3>Corpo</h3>
  <pre><code>sem corpo</code></pre>
  <h3>Resposta real</h3>
  <pre><code>{root_real_response}</code></pre>
  <h3>O que NÃO faz</h3>
  <p>Não entrega evento, tenant, manifesto ou dados de mercado; somente comprovação criptográfica publicada.</p>
</section>

<section class="card">
  <h2>O que este serviço não revela</h2>
  <ul>
    <li>Só valida o que a pessoa já tem em mãos.</li>
    <li>Não busca nem expõe documentos privados.</li>
    <li>Não entrega dados de mercado.</li>
  </ul>
</section>
"""
    corpo = corpo.replace("{verify_curl_payload}", verify_curl_payload)
    corpo = corpo.replace("{verify_real_response}", verify_real_response)
    corpo = corpo.replace("{root_real_response}", root_real_response)
    return _shell(corpo)


def _shell(corpo: str) -> str:
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE — API pública do verificador</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em}}h2{{margin-top:0}}h3{{margin:.8rem 0 .4rem;font-size:.95rem;color:var(--muted)}}
.muted{{color:var(--muted)}}code{{color:var(--accent);word-break:break-all}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.card{{background:var(--panel);padding:20px;border:1px solid #253149;border-radius:12px}}
pre{{background:#0b1320;border:1px solid #253149;border-radius:8px;padding:10px;overflow:auto}}
ul{{margin:0;padding-left:1.1rem}}
{CSS_NAV}
</style></head><body><main><h1>API PÚBLICA — verificador</h1>
{barra("/api")}
<p class="muted">Superfície de leitura: valida integridade criptográfica sem autenticação.</p>
<div class="grid">{corpo}</div>
</main></body></html>"""


def register_api_docs_routes(app: Any) -> None:
    """Anexa GET /api a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/api", response_class=HTMLResponse)
    def get_api_docs() -> str:
        return api_docs_page()
