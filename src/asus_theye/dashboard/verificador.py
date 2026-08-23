# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verificador público client-side — "refaça a conta" como gesto, não promessa.

Esta é a única página do site com JavaScript, e a exceção é o próprio ponto:
a verificação acontece NO NAVEGADOR DE QUEM VERIFICA. Nenhum byte do evento
colado sai da máquina do visitante — não há fetch, não há servidor, não há
token. É a materialização da tese do Ledger: você não precisa acreditar em
nós, nem sequer precisa da nossa infraestrutura para conferir.

A lógica é a MESMA de ``apps/public-verifier/worker.ts`` (obra própria deste
repositório), portada função a função: ``canonicalJson`` (RFC 8785 para o
domínio I-JSON do schema), ``sha256Hex`` via ``crypto.subtle``, ``verifyEvent``
(recomputa o hash do corpo sem ``event_hash_sha256`` e compara) e
``verifyChain`` (sequência contígua desde 1, gênese de zeros, cada elo
apontando o hash do anterior). Zero dependência externa: as APIs usadas —
``crypto.subtle.digest``, ``TextEncoder`` — são padrão de navegador.

O que a página aceita colado: um evento JSON único, uma lista JSON de eventos,
ou linhas JSONL (o formato exato de ``reports/markets/eventos.jsonl``).
"""

from __future__ import annotations

from .tema import pagina

# O script é gerado como bloco estático (não formatado com f-string) para as
# chaves de JS não colidirem com format(). Mantê-lo legível > minificado.
_SCRIPT = r"""
"use strict";
const GENESIS = "0".repeat(64);
const HEX64 = /^[0-9a-f]{64}$/;
const CAMPOS = ("schema_version event_id idempotency_key tenant_id sequence event_type action " +
  "occurred_at recorded_at actor_type actor_id_pseudonymous actor_role source_system resource_type " +
  "resource_id_pseudonymous resource_version jurisdiction legal_area_ids classification " +
  "retention_policy_id lawful_basis_reference content_hash_sha256 metadata_hash_sha256 " +
  "previous_event_hash_sha256 correlation_id causation_id model_provider model_name model_version " +
  "prompt_template_version source_citation_hashes human_review_status reviewer_pseudonymous " +
  "result_status error_code created_by_service build_version").split(" ");

function ehObjeto(v){ return typeof v === "object" && v !== null && !Array.isArray(v); }

function temSurrogateSolto(s){
  for (let i = 0; i < s.length; i++){
    const c = s.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff){
      const n = s.charCodeAt(i + 1);
      if (!(n >= 0xdc00 && n <= 0xdfff)) return true;
      i++;
    } else if (c >= 0xdc00 && c <= 0xdfff){ return true; }
  }
  return false;
}

function jsonCanonico(v){
  if (v === null) return "null";
  if (typeof v === "boolean" || typeof v === "string"){
    if (typeof v === "string" && temSurrogateSolto(v)) throw new Error("string fora do I-JSON");
    return JSON.stringify(v);
  }
  if (typeof v === "number"){
    if (!Number.isFinite(v) || (Number.isInteger(v) && !Number.isSafeInteger(v)))
      throw new Error("número fora do domínio I-JSON");
    return JSON.stringify(Object.is(v, -0) ? 0 : v);
  }
  if (Array.isArray(v)) return "[" + v.map(jsonCanonico).join(",") + "]";
  if (ehObjeto(v)){
    return "{" + Object.keys(v).sort().map(function(k){
      if (temSurrogateSolto(k)) throw new Error("chave fora do I-JSON");
      return JSON.stringify(k) + ":" + jsonCanonico(v[k]);
    }).join(",") + "}";
  }
  throw new Error("valor JSON não suportado");
}

async function sha256Hex(texto){
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return Array.from(new Uint8Array(d)).map(function(b){ return b.toString(16).padStart(2, "0"); }).join("");
}

async function verificarEvento(ev){
  if (!ehObjeto(ev)) return { ok:false, motivo:"evento deve ser um objeto JSON" };
  const faltando = CAMPOS.filter(function(c){ return !(c in ev); });
  if (faltando.length) return { ok:false, motivo:"evento sem campo obrigatório: " + faltando[0] };
  if (!Number.isSafeInteger(ev.sequence) || ev.sequence < 1)
    return { ok:false, motivo:"sequence deve ser inteiro positivo" };
  if (typeof ev.event_hash_sha256 !== "string" || !HEX64.test(ev.event_hash_sha256))
    return { ok:false, motivo:"event_hash_sha256 não é SHA-256 hexadecimal minúsculo" };
  const corpo = Object.assign({}, ev);
  delete corpo.event_hash_sha256;
  let esperado;
  try { esperado = await sha256Hex(jsonCanonico(corpo)); }
  catch (e){ return { ok:false, motivo:"evento fora do domínio I-JSON canônico" }; }
  if (esperado !== ev.event_hash_sha256)
    return { ok:false, motivo:"hash esperado " + esperado + ", recebido " + ev.event_hash_sha256 };
  return { ok:true, motivo:"hash do evento válido" };
}

async function verificarCadeia(evs){
  if (!Array.isArray(evs)) return { ok:false, motivo:"esperava lista de eventos" };
  if (evs.length === 0) return { ok:true, motivo:"cadeia vazia válida" };
  if (!evs.every(ehObjeto)) return { ok:false, motivo:"cada evento deve ser um objeto JSON" };
  const ordenados = evs.slice().sort(function(a, b){ return Number(a.sequence) - Number(b.sequence); });
  const tenant = ordenados[0].tenant_id;
  let seqEsperada = Number(ordenados[0].sequence);
  let hashAnterior = seqEsperada === 1 ? GENESIS : null;
  for (const ev of ordenados){
    if (Number(ev.sequence) !== seqEsperada)
      return { ok:false, motivo:"sequência quebrada: esperada " + seqEsperada + ", recebida " + ev.sequence };
    if (ev.tenant_id !== tenant)
      return { ok:false, motivo:"cadeia mistura tenants na sequência " + seqEsperada };
    if (hashAnterior !== null && ev.previous_event_hash_sha256 !== hashAnterior)
      return { ok:false, motivo:"encadeamento quebrado na sequência " + seqEsperada +
        ": hash anterior esperado " + hashAnterior + ", recebido " + ev.previous_event_hash_sha256 };
    const r = await verificarEvento(ev);
    if (!r.ok) return { ok:false, motivo:"sequência " + seqEsperada + ": " + r.motivo };
    hashAnterior = String(ev.event_hash_sha256);
    seqEsperada++;
  }
  const nota = Number(ordenados[0].sequence) === 1
    ? ordenados.length + " evento(s) íntegro(s) desde a gênese"
    : ordenados.length + " evento(s) íntegro(s) (recorte a partir da sequência " + ordenados[0].sequence + ")";
  return { ok:true, motivo:nota };
}

function interpretar(texto){
  const bruto = texto.trim();
  if (!bruto) throw new Error("cole um evento JSON, uma lista, ou linhas JSONL");
  try {
    const v = JSON.parse(bruto);
    return Array.isArray(v) ? v : [v];
  } catch (e) { /* tenta JSONL */ }
  const linhas = bruto.split("\n").map(function(l){ return l.trim(); }).filter(Boolean);
  return linhas.map(function(l, i){
    try { return JSON.parse(l); }
    catch (e){ throw new Error("linha " + (i + 1) + " não é JSON válido"); }
  });
}

async function aoConferir(){
  const saida = document.getElementById("resultado");
  const texto = document.getElementById("entrada").value;
  saida.className = "resultado";
  saida.textContent = "conferindo…";
  let eventos;
  try { eventos = interpretar(texto); }
  catch (e){ saida.className = "resultado quebrado"; saida.textContent = "✗ " + e.message; return; }
  const r = eventos.length === 1 ? await verificarEvento(eventos[0]) : await verificarCadeia(eventos);
  saida.className = "resultado " + (r.ok ? "valido" : "quebrado");
  saida.textContent = (r.ok ? "✓ VÁLIDO — " : "✗ QUEBRADO — ") + r.motivo;
}

document.getElementById("conferir").addEventListener("click", aoConferir);
"""

_ESTILO = """
<style>
.verificador textarea{width:100%;min-height:16rem;font-family:var(--mono);font-size:.72rem;
  line-height:1.5;padding:1rem;border:1px solid var(--regua);background:var(--papel-2);
  color:var(--tinta);resize:vertical;border-radius:2px}
.verificador textarea:focus{outline:2px solid var(--selo);outline-offset:2px}
.verificador button{font-family:var(--grotesca);font-weight:650;font-size:.94rem;
  letter-spacing:.04em;padding:.7rem 1.6rem;margin-top:.8rem;cursor:pointer;
  background:var(--selo);color:var(--papel);border:0;border-radius:2px}
.verificador button:hover{opacity:.92}
.resultado{font-family:var(--mono);font-size:.82rem;margin-top:1rem;padding:.9rem 1.1rem;
  border:1px solid var(--regua);word-break:break-all;line-height:1.6}
.resultado.valido{border-color:var(--selo);color:var(--selo);background:var(--selo-clara)}
.resultado.quebrado{border-color:var(--oxido);color:var(--oxido)}
</style>
"""


def verificador_page(*, estatico: bool = False) -> str:
    """A página do verificador — HTML autocontido, JS inline, zero rede."""
    corpo = f"""{_ESTILO}
<h1>Verificar</h1>
<p class="lede">Cole um evento da corrente — ou a corrente inteira — e confira aqui,
no seu navegador. <b>Nada sai da sua máquina</b>: não há servidor, não há token,
não há requisição. A conta é refeita localmente com <code>crypto.subtle</code>.</p>

<div class="verificador">
<label class="rotulo" for="entrada">evento JSON · lista JSON · linhas JSONL (o formato de eventos.jsonl)</label>
<textarea id="entrada" spellcheck="false"
placeholder='{{"schema_version": "1.0.0", "event_id": "…", "sequence": 1, …}}'></textarea>
<button id="conferir" type="button">Refazer a conta</button>
<div id="resultado" class="resultado" aria-live="polite">aguardando…</div>
</div>

<h2>O que é verificado</h2>
<ol class="passos">
<li><b>Hash do evento</b> — o corpo (sem <code>event_hash_sha256</code>) é serializado no JSON
canônico (RFC 8785, domínio I-JSON) e o SHA-256 recomputado precisa bater com o declarado.</li>
<li><b>Encadeamento</b> — numa lista, cada evento aponta o hash do anterior; o primeiro da
corrente aponta a gênese (64 zeros); a sequência é contígua e o tenant não muda.</li>
<li><b>O que um recorte prova</b> — um trecho colado sem a gênese prova a integridade
INTERNA do trecho; a ancoragem completa até a gênese exige a corrente desde o início.</li>
</ol>

<p class="nota">Esta é a única página do site com JavaScript — e é deliberado: o script roda
a verificação <em>na sua máquina</em>, que é o único lugar onde ela vale alguma coisa.
A mesma lógica roda no verificador de servidor (código aberto, AGPL-3.0-or-later, obra de
Mateus Menezes Figueiredo).</p>

<script>{_SCRIPT}</script>"""
    return pagina(
        titulo="ASUS THE EYE — verificar",
        corpo=corpo,
        rota="/verificar",
        estatico=estatico,
        descricao=(
            "Verificador público da corrente do THE EYE. Cole um evento e refaça a conta "
            "no seu navegador — sem servidor, sem token, sem confiança exigida."
        ),
    )
