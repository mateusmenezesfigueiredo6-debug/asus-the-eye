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

import json
import urllib.parse
from datetime import datetime, timezone
from typing import Any

from asus_theye.source_graph.fetcher import (
    FetchError,
    FetchPolicy,
    FetchRefusal,
    FetchResult,
    PoliteFetcher,
)

USER_AGENT = "asus-the-eye/0.2 (+mateusmenezesfigueiredo6@gmail.com)"
TIMEOUT = 30

_CONFIGURACAO = {
    "ror": {
        "license_id": "CC0-1.0",
        "terms_url": "https://ror.org/about/terms/",
        "max_bytes": 5_242_880,
    },
    "crossref": {
        "license_id": "CC0-1.0",
        "terms_url": "https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
        "max_bytes": 10_485_760,
    },
    "arxiv": {
        "license_id": "CC0-1.0",
        "terms_url": "https://info.arxiv.org/help/api/tou.html",
        "max_bytes": 5_242_880,
    },
    "doaj": {
        "license_id": "CC-BY-SA-4.0",
        "terms_url": "https://doaj.org/docs/api/",
        "max_bytes": 5_242_880,
    },
}


def _novo_fetcher(conector: str) -> PoliteFetcher:
    configuracao = _CONFIGURACAO[conector]
    policy = FetchPolicy(
        user_agent=USER_AGENT,
        max_bytes=configuracao["max_bytes"],
        timeout_seconds=TIMEOUT,
        access_basis=f"api_terms:{configuracao['terms_url']}",
    )
    return PoliteFetcher(
        policy=policy,
        connector_id=conector,
        license_id=configuracao["license_id"],
    )


# Uma instancia por conector preserva o limite de taxa entre chamadas sucessivas.
FETCHERS = {conector: _novo_fetcher(conector) for conector in _CONFIGURACAO}


class ConectorError(RuntimeError):
    """A fonte falhou ou devolveu formato inesperado."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _buscar(url: str, conector: str) -> FetchResult:
    """Busca pelo caminho educado e converte falha em erro do conector."""
    try:
        return FETCHERS[conector].get(url)
    except (FetchError, FetchRefusal) as error:
        raise ConectorError(f"{url}: {type(error).__name__}: {error}") from error


def _proveniencia(resultado: FetchResult) -> dict[str, Any]:
    return {
        "conector": resultado.connector_id,
        "url": resultado.url,
        "coletado_em_utc": resultado.retrieved_at,
        "sha256_resposta": resultado.content_hash_sha256,
    }


# ------------------------------------------------------------------ ROR
def ror(termo: str, limite: int = 5) -> dict[str, Any]:
    url = f"https://api.ror.org/organizations?query={urllib.parse.quote(termo)}"
    resultado = _buscar(url, "ror")
    d = json.loads(resultado.body)
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
            "itens": itens, "proveniencia": _proveniencia(resultado)}


# -------------------------------------------------------------- Crossref
def crossref(termo: str, limite: int = 5) -> dict[str, Any]:
    # O Crossref NAO tem busca por frase: aspas sao ignoradas (medido — "AI for
    # science" devolve os mesmos 15,6 milhoes com e sem). query.title restringe
    # ao titulo, que e o mais proximo disponivel, e o retorno declara isso.
    url = (f"https://api.crossref.org/works?query.title={urllib.parse.quote(termo)}"
           f"&rows={limite}&select=DOI,title,issued,type,publisher")
    resultado = _buscar(url, "crossref")
    msg = json.loads(resultado.body).get("message", {})
    itens = [{
        "doi": x.get("DOI"),
        "titulo": (x.get("title") or [""])[0][:120],
        "ano": ((x.get("issued") or {}).get("date-parts") or [[None]])[0][0],
        "tipo": x.get("type"),
        "editora": x.get("publisher"),
    } for x in (msg.get("items") or [])]
    return {"conector": "crossref", "total": msg.get("total-results", 0),
            "casamento": "titulo, palavras soltas — o Crossref nao suporta frase",
            "itens": itens, "proveniencia": _proveniencia(resultado)}


# ----------------------------------------------------------------- arXiv
def arxiv(termo: str, limite: int = 5) -> dict[str, Any]:
    """arXiv devolve Atom; extrai-se sem dependencia de parser externo."""
    import re
    # ASPAS IMPORTAM: sem elas o arXiv casa as palavras soltas. Medido em
    # 05/08/2026: "quantum machine learning" devolve 981.053 solto e 1.939 em
    # frase exata — diferenca de 500x. O numero solto nao significa nada.
    frase = urllib.parse.quote(f'"{termo}"')
    url = (f"https://export.arxiv.org/api/query?search_query=all:{frase}"
           f"&max_results={limite}")
    resultado = _buscar(url, "arxiv")
    texto = resultado.body.decode("utf-8", "ignore")
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
            "casamento": "frase exata",
            "itens": itens, "proveniencia": _proveniencia(resultado)}


# ------------------------------------------------------------------ DOAJ
def doaj(termo: str, limite: int = 5) -> dict[str, Any]:
    url = (f"https://doaj.org/api/search/journals/{urllib.parse.quote(termo)}"
           f"?pageSize={limite}")
    resultado = _buscar(url, "doaj")
    d = json.loads(resultado.body)
    itens = [{
        "titulo": ((x.get("bibjson") or {}).get("title") or "")[:120],
        "issn": (x.get("bibjson") or {}).get("eissn"),
        "pais": ((x.get("bibjson") or {}).get("publisher") or {}).get("country"),
        "acesso_aberto_verificado": True,  # estar no DOAJ ja e a verificacao
    } for x in (d.get("results") or [])]
    return {"conector": "doaj", "total": d.get("total", 0), "itens": itens,
            "proveniencia": _proveniencia(resultado)}


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
