# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: Banco Central do Brasil, série SGS 432 (meta Selic).

Este é o segundo conector que fecha o ciclo de medição de ponta a ponta: busca
a fonte OFICIAL declarada pela área ``juros`` no classificador e devolve
a meta publicada no último dia do mês — ou ``None`` quando o BCB ainda não
publicou. Nunca inventa: mês sem publicação é UNKNOWN, não zero.

A API é pública e sem chave: ``api.bcb.gov.br/dados/serie/bcdata.sgs.432``.
O transporte é injetável (``net.http.Transport``) para a suíte rodar offline.
"""

from __future__ import annotations

import calendar
import json

from asus_theye.net.http import HttpError, Transport, get_bytes

SERIE_SELIC = 432
URL_INTERVALO = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
    "?formato=json&dataInicial={data_inicial}&dataFinal={data_final}"
)
MAX_BYTES = 200_000
TIMEOUT = 30


class FonteSelicError(RuntimeError):
    """Resposta inesperada da fonte oficial. Sempre levanta — nunca degrada em valor."""


def _ano_mes(data_bcb: str) -> str:
    """Converte a data do BCB (``dd/mm/aaaa``) para ``aaaa-mm``."""
    try:
        _dia, mes, ano = data_bcb.split("/")
        return f"{ano}-{mes}"
    except ValueError as exc:
        raise FonteSelicError(f"data em formato inesperado do BCB: {data_bcb!r}") from exc


def _intervalo_mes(mes_referencia: str) -> tuple[str, str]:
    """Converte ``aaaa-mm`` no intervalo ``dd/mm/aaaa`` esperado pela API do BCB."""
    try:
        ano_txt, mes_txt = mes_referencia.split("-")
        ano, mes = int(ano_txt), int(mes_txt)
        ultimo_dia = calendar.monthrange(ano, mes)[1]
    except ValueError as exc:
        raise FonteSelicError(f"mês de referência em formato inesperado: {mes_referencia!r}") from exc
    return f"01/{mes:02d}/{ano:04d}", f"{ultimo_dia:02d}/{mes:02d}/{ano:04d}"


def selic_meta(mes_referencia: str, *, transport: Transport | None = None) -> float | None:
    """Meta da Selic publicada para ``mes_referencia`` (``aaaa-mm``).

    Devolve ``None`` se o mês ainda não foi publicado (UNKNOWN, não zero).
    Levanta :class:`FonteSelicError` para resposta malformada ou HTTP != 200 —
    fonte com erro não é fonte com valor.
    """
    data_inicial, data_final = _intervalo_mes(mes_referencia)
    url = URL_INTERVALO.format(serie=SERIE_SELIC, data_inicial=data_inicial, data_final=data_final)
    try:
        response = get_bytes(
            url, headers={"Accept": "application/json"}, timeout=TIMEOUT, max_bytes=MAX_BYTES, transport=transport
        )
    except HttpError as exc:
        raise FonteSelicError(f"fonte oficial inalcançável: {exc}") from exc
    if response.status != 200:
        raise FonteSelicError(f"fonte oficial respondeu HTTP {response.status} em {url}")

    try:
        pontos = json.loads(response.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FonteSelicError(f"resposta do BCB não é JSON válido ({exc})") from exc
    if not isinstance(pontos, list):
        raise FonteSelicError(f"resposta do BCB em formato inesperado: {type(pontos).__name__}")
    if not pontos:
        return None  # mês ainda não publicado — UNKNOWN over guess

    ultimo_valor: float | None = None
    for ponto in pontos:
        if not isinstance(ponto, dict) or "data" not in ponto or "valor" not in ponto:
            raise FonteSelicError(f"ponto em formato inesperado do BCB: {ponto!r}")
        if _ano_mes(str(ponto["data"])) != mes_referencia:
            raise FonteSelicError(f"ponto fora do mês consultado em {mes_referencia}: {ponto!r}")
        try:
            ultimo_valor = float(str(ponto["valor"]).replace(",", "."))
        except ValueError as exc:
            raise FonteSelicError(f"valor não numérico do BCB: {ponto['valor']!r}") from exc
    return ultimo_valor
