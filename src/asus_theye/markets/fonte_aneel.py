# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: ANEEL — bandeira tarifária da conta de luz.

A bandeira é o item mais direto da conta de luz que muda todo mês e que
qualquer pessoa entende sem explicação: verde não cobra adicional, amarela e
vermelha cobram. É uma das melhores fontes brasileiras que existem para
liquidar contrato — licença **ODbL** declarada no próprio portal de dados
abertos, competência mensal e valor que não se retifica depois de acionado.

BANDEIRA É CATEGÓRICA; O MOTOR COMPARA NÚMERO. A ponte é uma escada ordenada
pelo que a bandeira custa ao consumidor:

    0 Verde · 1 Amarela · 2 Vermelha P1 · 3 Vermelha P2 · 4 Escassez Hídrica

Assim "vem amarela ou pior?" vira ``nível >= 1`` — comparação objetiva sobre
uma ordem que a própria ANEEL define pelo adicional cobrado. A escada é
FECHADA: rótulo novo levanta em vez de virar zero, porque um valor que o
conector não entende não pode passar por "verde".

Nos 140 meses publicados (2015-01 a 2026-08): amarela ou pior em 52,1%,
vermelha ou pior em 35,0% — os dois dentro da faixa de exibição da casa.

O transporte é injetável (``net.http.Transport``) para a suíte rodar offline.
"""

from __future__ import annotations

import csv
import io
import re

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

URL_ACIONAMENTO = (
    "https://dadosabertos.aneel.gov.br/dataset/7f43a020-6dc5-44b8-80b4-d97eaa94436c"
    "/resource/0591b8f6-fe54-437b-b72b-1aa2efd46e42/download/bandeira-tarifaria-acionamento.csv"
)
MAX_BYTES = 2_000_000
TIMEOUT = 60

MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

#: Escada de severidade, ordenada pelo adicional que a bandeira cobra.
#: Fechada de propósito: rótulo desconhecido levanta, nunca vira 0 (verde).
NIVEL_BANDEIRA = {
    "verde": 0.0,
    "amarela": 1.0,
    "vermelha p1": 2.0,
    "vermelha p2": 3.0,
    "escassez hídrica": 4.0,
}


class FonteAneelError(FonteError):
    """Resposta inesperada da ANEEL. Sempre levanta — nunca degrada em valor."""


def _competencia(mes_referencia: str) -> str:
    """``aaaa-mm`` -> ``aaaa-mm-01``, como a ANEEL grava a competência."""
    if not isinstance(mes_referencia, str) or not MES_RE.match(mes_referencia):
        raise FonteAneelError(f"mês de referência em formato inesperado: {mes_referencia!r}")
    return f"{mes_referencia}-01"


def nivel_da_bandeira(mes_referencia: str, *, transport: Transport | None = None) -> float | None:
    """Nível da bandeira tarifária acionada em ``mes_referencia`` (``aaaa-mm``).

    Devolve ``None`` quando a ANEEL ainda não publicou aquela competência — o
    acionamento entra no dataset quando é decidido, e mês futuro simplesmente
    não está lá. Isso é UNKNOWN, nunca "verde".
    """
    alvo = _competencia(mes_referencia)
    try:
        response = get_bytes(
            URL_ACIONAMENTO,
            headers={"Accept": "text/csv"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteAneelError(f"fonte oficial inalcançável: {exc}") from exc
    if response.status != 200:
        raise FonteAneelError(f"ANEEL respondeu HTTP {response.status} em {URL_ACIONAMENTO}")

    try:
        texto = response.body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FonteAneelError(f"CSV da ANEEL não decodifica em UTF-8 ({exc})") from exc

    linhas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
    if not linhas:
        raise FonteAneelError("CSV da ANEEL veio vazio")
    for campo in ("DatCompetencia", "NomBandeiraAcionada"):
        if campo not in linhas[0]:
            raise FonteAneelError(
                f"CSV da ANEEL sem a coluna {campo!r} — o layout mudou: {sorted(linhas[0])}"
            )

    encontradas = [linha for linha in linhas if str(linha["DatCompetencia"]).strip() == alvo]
    if not encontradas:
        return None  # competência ainda não acionada — UNKNOWN over guess
    if len(encontradas) > 1:
        raise FonteAneelError(f"a competência {alvo} aparece {len(encontradas)} vezes no CSV")

    rotulo = str(encontradas[0]["NomBandeiraAcionada"]).strip()
    nivel = NIVEL_BANDEIRA.get(rotulo.casefold())
    if nivel is None:
        raise FonteAneelError(
            f"bandeira {rotulo!r} não está na escada conhecida "
            f"({sorted(NIVEL_BANDEIRA)}) — não liquida até alguém conferir"
        )
    return nivel
