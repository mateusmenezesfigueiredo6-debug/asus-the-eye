#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rastreador de desdobramentos (plano F6) — publicações novas dos autores do corpus.

Varre, via API pública do Crossref, as publicações de 2025+ dos ~30 autores
mais relevantes do corpus da casa (REF-02/REF-03) e tabula o resultado em
Markdown com hyperlink por DOI, uma seção por autor.

POR QUE NÃO REUSA O CONECTOR ACADÊMICO: `asus_theye.source_graph.connectors.
academico.crossref()` só expõe busca por TÍTULO (`query.title`) — não existe
busca por autor lá. Este script fala direto com a API pública usando
`asus_theye.net.http.get_bytes`, herdando a mesma etiqueta do conector:
user-agent que identifica o cliente, limite de tamanho obrigatório e
proveniência (timestamp UTC + sha256 da resposta) registrada na saída.

REGRAS QUE ESTE SCRIPT RESPEITA
  1. Ausência declarada, nunca omitida: autor sem publicação 2025+ aparece
     listado no fim do relatório, não some em silêncio.
  2. Falha de rede de um autor NÃO derruba os demais: o erro vira texto na
     seção daquele autor.
  3. Educação com a API: pausa fixa entre autores e contato no parâmetro
     `mailto` (ver CONTATO_POLITE_POOL).
  4. Filtro leve de homônimos: se o campo `author` do work não contém o
     sobrenome exato do autor buscado, o work é pulado.

USO:
  python3 scripts/rastrear_desdobramentos.py

Sem dependência nova: stdlib + asus_theye.net.http.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

try:
    from asus_theye.net.http import HttpError, get_bytes
except ImportError as erro:  # pragma: no cover - depende do layout do repo
    raise SystemExit(
        f"rastrear_desdobramentos: não achei asus_theye em {RAIZ / 'src'} ({erro}); "
        "rode a partir do repositório asus_the_eye ou exporte PYTHONPATH=src"
    ) from erro

# ------------------------------------------------------------------ constantes

API_CROSSREF = "https://api.crossref.org/works"

#: O parâmetro `mailto` inscreve a chamada no "polite pool" do Crossref — a
#: fila prioritária, com limites mais generosos, para clientes que se
#: identificam com um contato (documentado em
#: https://api.crossref.org/swagger-ui/index.html e no blog do Crossref).
#: Precedente da casa (connectors/academico.py): o contato é trocável via
#: ambiente sem editar código; aqui o padrão é o contato do titular porque o
#: plano F6 pediu explicitamente a fila educada.
CONTATO_POLITE_POOL = os.environ.get("ASUS_THE_EYE_CONTATO", "").strip() or "mateusmenezesfigueiredo7@gmail.com"

#: Mesmo formato exigido pelo FetchPolicy da casa: cliente + contato.
USER_AGENT = f"asus-the-eye/0.2 (+{CONTATO_POLITE_POOL})"

#: Só interessa desdobramento NOVO: publicado a partir desta data.
DATA_CORTE = "2025-01-01"
ANO_MINIMO = 2025

#: Até quantos works pedir por autor (o filtro de homônimos pode reduzir).
OBRAS_POR_AUTOR = 5

#: Pausa entre autores — educação com a API, além do polite pool.
PAUSA_ENTRE_AUTORES_SEGUNDOS = 1.0

#: Mesmos limites do conector Crossref da casa (academico.py).
TIMEOUT_SEGUNDOS = 30
MAX_BYTES = 10_485_760

#: Título truncado na tabela para o Markdown continuar legível.
LIMITE_TITULO = 160

SAIDA = Path("/home/sexexes/Área de trabalho/desdobramentos-autores-20260902.md")

#: Os ~30 autores mais relevantes do corpus REF-02/REF-03 (lista fixa do F6).
AUTORES = [
    "Andrew Gelman",
    "Rob J. Hyndman",
    "Drew A. Linzer",
    "Robin Hanson",
    "Philip E. Tetlock",
    "Justin Wolfers",
    "Eric Zitzewitz",
    "Aki Vehtari",
    "Anastasios N. Angelopoulos",
    "Stephen Bates",
    "Tianqi Chen",
    "Gerd Gigerenzer",
    "Baruch Fischhoff",
    "David Budescu",
    "Ellen Peters",
    "David Spiegelhalter",
    "Roger Koenker",
    "Christoph Bergmeir",
    "Vitor Cerqueira",
    "João Gama",
    "Chip Huyen",
    "Christoph Molnar",
    "Barbara Mellers",
    "Yuling Yao",
    "Nicolai Meinshausen",
    "Lukas F. Stoetzer",
    "Chris Hanretty",
    "Abraham Othman",
    "David Pennock",
    "Philip Newall",
]


# ------------------------------------------------------------------ estruturas


@dataclass
class Achado:
    titulo: str
    ano: int | None
    revista: str
    doi: str | None

    @property
    def link(self) -> str | None:
        return f"https://doi.org/{self.doi}" if self.doi else None


@dataclass
class ResultadoAutor:
    nome: str
    achados: list[Achado] = field(default_factory=list)
    erro: str | None = None
    consultado_em_utc: str | None = None
    sha256_resposta: str | None = None


# ------------------------------------------------------------------- helpers


def _utc_agora() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalizar(texto: str) -> str:
    """Minúsculas sem acento — 'Gama' casa com 'gama', 'João' vira 'joao'."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold()


def _sobrenome(nome: str) -> str:
    return _normalizar(nome.split()[-1])


def _contem_sobrenome(obra: dict[str, Any], sobrenome: str) -> bool:
    """Filtro leve de homônimos: o campo author precisa conter o sobrenome exato."""
    for autor in obra.get("author") or []:
        if _normalizar(autor.get("family") or "") == sobrenome:
            return True
        # Entradas sem given/family (raras, ex.: nome de grupo) vêm em `name`.
        if sobrenome in _normalizar(autor.get("name") or "").split():
            return True
    return False


def _ano_da_obra(obra: dict[str, Any]) -> int | None:
    partes = ((obra.get("issued") or {}).get("date-parts") or [[None]])[0]
    return partes[0] if partes and isinstance(partes[0], int) else None


def _url_consulta(nome: str) -> str:
    parametros = urllib.parse.urlencode(
        {
            "query.author": nome,
            "filter": f"from-pub-date:{DATA_CORTE}",
            "sort": "published",
            "order": "desc",
            "rows": OBRAS_POR_AUTOR,
            "select": "DOI,title,issued,container-title,author",
            "mailto": CONTATO_POLITE_POOL,  # polite pool — ver constante
        }
    )
    return f"{API_CROSSREF}?{parametros}"


def _celula(texto: str) -> str:
    """Escapa o que quebraria a célula de tabela Markdown."""
    return " ".join(texto.split()).replace("|", "\\|")


# -------------------------------------------------------------------- coleta


def rastrear_autor(nome: str) -> ResultadoAutor:
    resultado = ResultadoAutor(nome=nome)
    url = _url_consulta(nome)
    try:
        resposta = get_bytes(
            url,
            headers={"user-agent": USER_AGENT, "accept": "application/json"},
            timeout=TIMEOUT_SEGUNDOS,
            max_bytes=MAX_BYTES,
        )
        if resposta.status != 200:
            raise HttpError(f"HTTP {resposta.status}: {url}", status=resposta.status)
        mensagem = json.loads(resposta.body).get("message", {})
    except (HttpError, ValueError) as erro:
        # Falha de UM autor não derruba o resto: vira texto na seção dele.
        resultado.erro = f"{type(erro).__name__}: {erro}"
        return resultado

    resultado.consultado_em_utc = _utc_agora()
    resultado.sha256_resposta = hashlib.sha256(resposta.body).hexdigest()

    sobrenome = _sobrenome(nome)
    for obra in mensagem.get("items") or []:
        if not _contem_sobrenome(obra, sobrenome):
            continue  # homônimo provável
        ano = _ano_da_obra(obra)
        if ano is not None and ano < ANO_MINIMO:
            continue  # defesa extra: o filtro da API usa outras datas além de issued
        resultado.achados.append(
            Achado(
                titulo=((obra.get("title") or [""])[0] or "(sem título)")[:LIMITE_TITULO],
                ano=ano,
                revista=(obra.get("container-title") or [""])[0] or "—",
                doi=obra.get("DOI"),
            )
        )
    return resultado


# ------------------------------------------------------------------ relatório


def _secao_autor(resultado: ResultadoAutor) -> list[str]:
    linhas = [f"## {resultado.nome}", ""]
    if resultado.erro:
        linhas += [f"Erro na consulta (os demais autores seguiram normalmente): `{resultado.erro}`", ""]
        return linhas
    linhas += ["| Ano | Título | Revista | DOI |", "|---|---|---|---|"]
    for achado in resultado.achados:
        doi = f"[{achado.doi}]({achado.link})" if achado.doi else "sem DOI"
        ano = str(achado.ano) if achado.ano is not None else "s.d."
        linhas.append(f"| {ano} | {_celula(achado.titulo)} | {_celula(achado.revista)} | {doi} |")
    if resultado.consultado_em_utc:
        linhas += ["", f"Consulta: {resultado.consultado_em_utc} · sha256 da resposta: `{resultado.sha256_resposta}`"]
    linhas.append("")
    return linhas


def montar_markdown(resultados: list[ResultadoAutor]) -> str:
    com_achados = [r for r in resultados if r.achados]
    sem_achados = [r for r in resultados if not r.achados and not r.erro]
    com_erro = [r for r in resultados if r.erro]

    linhas = [
        "# Desdobramentos dos autores do corpus — publicações 2025+",
        "",
        f"Gerado em {_utc_agora()} por `scripts/rastrear_desdobramentos.py` (plano F6).",
        f"Fonte: API pública do Crossref (`{API_CROSSREF}`), busca `query.author`, "
        f"filtro `from-pub-date:{DATA_CORTE}`, até {OBRAS_POR_AUTOR} works por autor, "
        "polite pool via `mailto`.",
        "Filtro leve de homônimos: work cujo campo author não contém o sobrenome exato foi pulado.",
        "",
        f"Autores varridos: {len(resultados)} · com publicação 2025+: {len(com_achados)} · "
        f"sem publicação 2025+: {len(sem_achados)} · com erro de consulta: {len(com_erro)}",
        "",
    ]
    for resultado in com_achados:
        linhas += _secao_autor(resultado)
    for resultado in com_erro:
        linhas += _secao_autor(resultado)
    if sem_achados:
        # Ausência declarada, nunca omitida.
        linhas += ["## Sem publicação 2025+ encontrada", ""]
        linhas += [f"- {r.nome} — sem publicação 2025+ encontrada" for r in sem_achados]
        linhas.append("")
    return "\n".join(linhas)


def main() -> int:
    resultados: list[ResultadoAutor] = []
    for indice, nome in enumerate(AUTORES):
        if indice > 0:
            time.sleep(PAUSA_ENTRE_AUTORES_SEGUNDOS)
        resultado = rastrear_autor(nome)
        resultados.append(resultado)
        situacao = f"ERRO ({resultado.erro})" if resultado.erro else f"{len(resultado.achados)} achado(s)"
        print(f"[{indice + 1:2d}/{len(AUTORES)}] {nome}: {situacao}")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(montar_markdown(resultados), encoding="utf-8")
    print(f"\nRelatório escrito em: {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
