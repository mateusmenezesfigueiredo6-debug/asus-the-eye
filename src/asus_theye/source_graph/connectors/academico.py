"""Conectores da trilha academica — ROR, Crossref, arXiv e DOAJ.

Ate aqui a trilha academica estava em 0,0%: os conectores existiam declarados em
`data/source-graph/connectors.json`, sem implementacao. Este modulo implementa
os quatro que dispensam chave e cujas APIs responderam 200 na verificacao.

O QUE CADA UM TRAZ

  ROR       registro aberto de instituicoes de pesquisa; devolve identificador
            estavel, pais e tipo. Serve para ancorar autoridade institucional
            sem depender de ranking de popularidade.
  Crossref  metadados de publicacao com DOI. Serve para datar producao e
            verificar existencia, nunca para contar citacao como prestigio.
  arXiv     preprints; serve para achar trabalho recente antes da revisao por
            pares, com a ressalva de que preprint NAO e evidencia revisada.
  DOAJ      periodicos de acesso aberto verificados; serve para saber se uma
            revista tem politica aberta declarada.

REGRAS QUE ESTE MODULO RESPEITA (vindas do AGENTS.md e do github.py)

  1. Metrica social nunca vira score. Contagem de citacao e coletada como
     contexto factual e marcada como tal; ranquear por popularidade e proibido.
  2. Toda resposta guarda proveniencia: URL exata, timestamp UTC e SHA-256 do
     corpo. Sem isso o dado nao entra no grafo.
  3. User-agent identifica o cliente e um contato, como exige o fetcher.
  4. Falha de rede vira registro de falha, nunca zero silencioso.

Uso: python3 -m asus_theye.source_graph.connectors.academico <termo>
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

USER_AGENT = "asus-the-eye/0.2 (+mateusmenezesfigueiredo6@gmail.com)"
TIMEOUT = 30


class ConectorError(RuntimeError):
    """A fonte falhou ou devolveu formato inesperado."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _buscar(url: str) -> tuple[bytes, str]:
    """Devolve corpo e proveniencia. Nunca engole erro."""
    pedido = urllib.request.Request(url, headers={"user-agent": USER_AGENT})
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT) as r:
            corpo = r.read()
    except Exception as error:  # noqa: BLE001 — a causa vai no registro
        raise ConectorError(f"{url}: {type(error).__name__}") from error
    return corpo, hashlib.sha256(corpo).hexdigest()


def _proveniencia(url: str, sha: str, conector: str) -> dict[str, Any]:
    return {"conector": conector, "url": url, "coletado_em_utc": _utc_now(),
            "sha256_resposta": sha}


# ------------------------------------------------------------------ ROR
def ror(termo: str, limite: int = 5) -> dict[str, Any]:
    url = f"https://api.ror.org/organizations?query={urllib.parse.quote(termo)}"
    corpo, sha = _buscar(url)
    d = json.loads(corpo)
    # A v2 do ROR trocou `name` por `names[]` e `country` por `locations[]`.
    # Sem este ajuste o conector devolvia nome e pais nulos em silencio.
    def _nome(x):
        for n in x.get("names") or []:
            if "ror_display" in (n.get("types") or []):
                return n.get("value")
        return next((n.get("value") for n in (x.get("names") or [])), None)

    def _pais(x):
        loc = (x.get("locations") or [{}])[0]
        return (loc.get("geonames_details") or {}).get("country_name")

    itens = [{
        "ror_id": x.get("id"),
        "nome": _nome(x),
        "pais": _pais(x),
        "tipos": x.get("types", []),
    } for x in (d.get("items") or [])[:limite]]
    return {"conector": "ror", "total": (d.get("number_of_results") or 0),
            "itens": itens, "proveniencia": _proveniencia(url, sha, "ror")}


# -------------------------------------------------------------- Crossref
def crossref(termo: str, limite: int = 5) -> dict[str, Any]:
    url = (f"https://api.crossref.org/works?query={urllib.parse.quote(termo)}"
           f"&rows={limite}&select=DOI,title,issued,type,publisher")
    corpo, sha = _buscar(url)
    msg = json.loads(corpo).get("message", {})
    itens = [{
        "doi": x.get("DOI"),
        "titulo": (x.get("title") or [""])[0][:120],
        "ano": ((x.get("issued") or {}).get("date-parts") or [[None]])[0][0],
        "tipo": x.get("type"),
        "editora": x.get("publisher"),
    } for x in (msg.get("items") or [])]
    return {"conector": "crossref", "total": msg.get("total-results", 0),
            "itens": itens, "proveniencia": _proveniencia(url, sha, "crossref")}


# ----------------------------------------------------------------- arXiv
def arxiv(termo: str, limite: int = 5) -> dict[str, Any]:
    """arXiv devolve Atom; extrai-se sem dependencia de parser externo."""
    import re
    url = (f"https://export.arxiv.org/api/query?search_query=all:"
           f"{urllib.parse.quote(termo)}&max_results={limite}")
    corpo, sha = _buscar(url)
    texto = corpo.decode("utf-8", "ignore")
    total_m = re.search(r"<opensearch:totalResults[^>]*>(\d+)<", texto)
    entradas = re.findall(r"<entry>(.*?)</entry>", texto, re.S)[:limite]
    itens = []
    for e in entradas:
        t = re.search(r"<title>(.*?)</title>", e, re.S)
        i = re.search(r"<id>(.*?)</id>", e)
        p = re.search(r"<published>(.*?)</published>", e)
        itens.append({
            "id": i.group(1) if i else None,
            "titulo": " ".join(t.group(1).split())[:120] if t else None,
            "publicado": p.group(1)[:10] if p else None,
            "revisado_por_pares": False,  # preprint nunca e evidencia revisada
        })
    return {"conector": "arxiv", "total": int(total_m.group(1)) if total_m else None,
            "itens": itens, "proveniencia": _proveniencia(url, sha, "arxiv")}


# ------------------------------------------------------------------ DOAJ
def doaj(termo: str, limite: int = 5) -> dict[str, Any]:
    url = (f"https://doaj.org/api/search/journals/{urllib.parse.quote(termo)}"
           f"?pageSize={limite}")
    corpo, sha = _buscar(url)
    d = json.loads(corpo)
    itens = [{
        "titulo": ((x.get("bibjson") or {}).get("title") or "")[:120],
        "issn": (x.get("bibjson") or {}).get("eissn"),
        "pais": ((x.get("bibjson") or {}).get("publisher") or {}).get("country"),
        "acesso_aberto_verificado": True,  # estar no DOAJ ja e a verificacao
    } for x in (d.get("results") or [])]
    return {"conector": "doaj", "total": d.get("total", 0), "itens": itens,
            "proveniencia": _proveniencia(url, sha, "doaj")}


CONECTORES = {"ror": ror, "crossref": crossref, "arxiv": arxiv, "doaj": doaj}


def coletar(termo: str, limite: int = 5) -> dict[str, Any]:
    """Roda os quatro. Falha de um nao derruba os outros — e fica registrada."""
    saida, falhas = {}, {}
    for nome, fn in CONECTORES.items():
        try:
            saida[nome] = fn(termo, limite)
        except ConectorError as e:
            falhas[nome] = str(e)
    return {"termo": termo, "gerado_em_utc": _utc_now(),
            "conectores_ok": sorted(saida), "conectores_com_falha": falhas,
            "resultados": saida}


if __name__ == "__main__":
    import sys
    termo = sys.argv[1] if len(sys.argv) > 1 else "legal informatics"
    r = coletar(termo)
    print(f"termo: {r['termo']}")
    print(f"ok: {r['conectores_ok']}  falhas: {list(r['conectores_com_falha'])}")
    for nome, res in r["resultados"].items():
        print(f"\n{nome} — total {res['total']}")
        for it in res["itens"][:3]:
            print("   ", json.dumps(it, ensure_ascii=False)[:110])
