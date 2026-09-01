# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Netflix Top 10 por país — dado PRIMÁRIO publicado pela própria Netflix.

Fonte de liquidação da área ``cultura-streaming``: o arquivo
``all-weeks-countries.tsv`` que a Netflix publica em tudum.com — não é
raspagem de página, é o dataset oficial deles, uma linha por
(país, semana, categoria, posição 1..10).

Colunas conferidas ao vivo em 01/09/2026:
``country_name  country_iso2  week  category  weekly_rank  show_title
season_title  cumulative_weeks_in_top_10``. Mudança de layout LEVANTA —
liquidar contra coluna errada é pior que não liquidar.

Doutrina de sempre: semana ainda não publicada devolve ``None`` (UNKNOWN,
não zero — a Netflix publica com ~3 dias de atraso); resposta malformada ou
truncada levanta. O servidor deles recusa HEAD (403) mas serve GET normal.
"""

from __future__ import annotations

import csv
import io

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

URL_TOP10 = "https://www.netflix.com/tudum/top10/data/all-weeks-countries.tsv"
#: O TSV completo cobre ~95 países × todas as semanas desde 2021 — dezenas de
#: MB e crescendo ~40 KB/semana. O teto tem folga de anos; estourar levanta
#: em vez de truncar (contrato de net/http).
MAX_BYTES = 200_000_000
TIMEOUT = 180

COLUNAS_ESPERADAS = (
    "country_name",
    "country_iso2",
    "week",
    "category",
    "weekly_rank",
    "show_title",
    "season_title",
    "cumulative_weeks_in_top_10",
)

CATEGORIAS = frozenset({"Films", "TV"})


class FonteNetflixError(FonteError):
    """Resposta malformada ou fora do ar. Sempre levanta — nunca vira palpite."""


def _baixar_tsv(transport: Transport | None) -> str:
    try:
        response = get_bytes(
            URL_TOP10,
            headers={"Accept": "text/tab-separated-values"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteNetflixError(f"Netflix Top 10 inalcançável: {exc}") from exc
    if response.status != 200:
        raise FonteNetflixError(f"Netflix Top 10 respondeu HTTP {response.status}")
    try:
        return response.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FonteNetflixError(f"TSV da Netflix não decodifica como UTF-8 ({exc})") from exc


def semanas_no_topo(
    semana: str,
    *,
    pais: str = "BR",
    categoria: str = "Films",
    posicao: int = 1,
    transport: Transport | None = None,
) -> int | None:
    """``cumulative_weeks_in_top_10`` do título na ``posicao`` — ou ``None``.

    ``semana`` no formato ``aaaa-mm-dd`` (o domingo que abre a semana, como a
    própria Netflix rotula). ``None`` significa UMA coisa: a Netflix ainda não
    publicou aquela semana para aquele país. Semana publicada SEM a posição
    pedida é malformação e levanta — o Top 10 completo é invariante do dataset.
    """
    if categoria not in CATEGORIAS:
        raise FonteNetflixError(f"categoria deve ser uma de {sorted(CATEGORIAS)}, veio {categoria!r}")
    if not 1 <= posicao <= 10:
        raise FonteNetflixError(f"posição deve estar em [1, 10], veio {posicao}")
    if len(semana) != 10 or semana[4] != "-" or semana[7] != "-":
        raise FonteNetflixError(f"semana deve ser 'aaaa-mm-dd', veio {semana!r}")

    leitor = csv.reader(io.StringIO(_baixar_tsv(transport)), delimiter="\t")
    try:
        cabecalho = tuple(next(leitor))
    except StopIteration as exc:
        raise FonteNetflixError("TSV da Netflix veio vazio") from exc
    if cabecalho != COLUNAS_ESPERADAS:
        raise FonteNetflixError(
            f"layout do TSV mudou: esperado {COLUNAS_ESPERADAS}, veio {cabecalho} — "
            "conferir a fonte antes de liquidar qualquer contrato"
        )

    semana_existe = False
    for linha in leitor:
        if len(linha) != len(COLUNAS_ESPERADAS):
            continue  # linha rasgada no meio do arquivo não decide contrato
        if linha[1] != pais or linha[2] != semana or linha[3] != categoria:
            continue
        semana_existe = True
        if int(linha[4]) == posicao:
            try:
                return int(linha[7])
            except ValueError as exc:
                raise FonteNetflixError(
                    f"cumulative_weeks_in_top_10 não numérico: {linha[7]!r} em {linha[5]!r}"
                ) from exc
    if semana_existe:
        raise FonteNetflixError(
            f"semana {semana} publicada para {pais}/{categoria} mas sem posição {posicao} — "
            "Top 10 incompleto é malformação, não ausência"
        )
    return None  # semana ainda não publicada — UNKNOWN over guess
