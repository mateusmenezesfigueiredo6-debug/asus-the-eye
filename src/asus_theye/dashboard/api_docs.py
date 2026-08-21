# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Painel do dashboard: documentação pública da API do verificador."""

from __future__ import annotations

from typing import Any

from .tema import pagina


def api_docs_page(*, estatico: bool = False) -> str:
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
    return pagina(
        titulo="ASUS THE EYE — API pública",
        corpo="<h1>API PÚBLICA — verificador</h1>"
        "<p class='lede'>leitura anônima: valida a integridade sem autenticação</p>" + corpo,
        rota="/api",
        estatico=estatico,
    )


def register_api_docs_routes(app: Any) -> None:
    """Anexa GET /api a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/api", response_class=HTMLResponse)
    def get_api_docs() -> str:
        return api_docs_page()
