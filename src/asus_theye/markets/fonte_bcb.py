# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: Banco Central do Brasil, série SGS 433 (IPCA mensal).

Este é o primeiro conector que fecha o ciclo de medição de ponta a ponta: busca
a fonte OFICIAL declarada pela área ``macroeconomia`` no classificador e devolve
o valor publicado do mês — ou ``None`` quando o BCB ainda não publicou. Nunca
inventa: mês sem publicação é UNKNOWN, não zero.

A API é pública e sem chave: ``api.bcb.gov.br/dados/serie/bcdata.sgs.433``.
O transporte é injetável (``net.http.Transport``) para a suíte rodar offline.
"""

from __future__ import annotations

import json

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

SERIE_IPCA = 433
URL_ULTIMOS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados/ultimos/{n}?formato=json"
MAX_BYTES = 200_000
TIMEOUT = 30
# Limite documentado pela propria API (erro SGSNegocioException):
# "A quantidade maxima de valores deve ser 20".
JANELA_MAXIMA = 20


class FonteBCBError(FonteError):
    """Resposta inesperada da fonte oficial. Sempre levanta — nunca degrada em valor."""


def _ano_mes(data_bcb: str) -> str:
    """Converte a data do BCB (``dd/mm/aaaa``) para ``aaaa-mm``."""
    try:
        _dia, mes, ano = data_bcb.split("/")
        return f"{ano}-{mes}"
    except ValueError as exc:
        raise FonteBCBError(f"data em formato inesperado do BCB: {data_bcb!r}") from exc


def ipca_mensal(
    mes_referencia: str,
    *,
    serie: int = SERIE_IPCA,
    janela: int = 12,
    transport: Transport | None = None,
) -> float | None:
    """Variação mensal publicada do IPCA para ``mes_referencia`` (``aaaa-mm``).

    Devolve ``None`` se o mês ainda não foi publicado (UNKNOWN, não zero).
    Levanta :class:`FonteBCBError` para resposta malformada ou HTTP != 200 —
    fonte com erro não é fonte com valor.
    """
    if not 1 <= janela <= JANELA_MAXIMA:
        raise FonteBCBError(f"janela deve estar em [1, {JANELA_MAXIMA}] (limite da API do BCB), veio {janela}")
    url = URL_ULTIMOS.format(serie=serie, n=janela)
    try:
        response = get_bytes(
            url, headers={"Accept": "application/json"}, timeout=TIMEOUT, max_bytes=MAX_BYTES, transport=transport
        )
    except HttpError as exc:
        raise FonteBCBError(f"fonte oficial inalcançável: {exc}") from exc
    if response.status != 200:
        raise FonteBCBError(f"fonte oficial respondeu HTTP {response.status} em {url}")

    try:
        pontos = json.loads(response.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FonteBCBError(f"resposta do BCB não é JSON válido ({exc})") from exc
    if not isinstance(pontos, list):
        raise FonteBCBError(f"resposta do BCB em formato inesperado: {type(pontos).__name__}")

    por_mes: dict[str, list[float]] = {}
    for ponto in pontos:
        if not isinstance(ponto, dict) or "data" not in ponto or "valor" not in ponto:
            raise FonteBCBError(f"ponto em formato inesperado do BCB: {ponto!r}")
        try:
            valor = float(str(ponto["valor"]).replace(",", "."))
        except ValueError as exc:
            raise FonteBCBError(f"valor não numérico do BCB: {ponto['valor']!r}") from exc
        por_mes.setdefault(_ano_mes(str(ponto["data"])), []).append(valor)

    if not por_mes:
        raise FonteBCBError("série vazia do BCB — resposta sem nenhum ponto")

    if mes_referencia in por_mes:
        valores = por_mes[mes_referencia]
        if len(set(valores)) > 1:
            raise FonteBCBError(f"mês {mes_referencia} duplicado com valores divergentes na série: {valores}")
        return valores[0]

    # None significa UMA coisa só: mês ainda não publicado. Mês anterior à
    # janela consultada é 'inconsultável por aqui' — e isso levanta, senão um
    # mercado antigo ficaria EM_RESOLUCAO para sempre parecendo UNKNOWN.
    mais_antigo = min(por_mes)  # "aaaa-mm" ordena lexicograficamente
    if mes_referencia < mais_antigo:
        raise FonteBCBError(
            f"janela de {janela} pontos não alcança {mes_referencia} "
            f"(mais antigo consultado: {mais_antigo}) — aumente a janela (máx. {JANELA_MAXIMA}) "
            "ou consulte por intervalo de datas"
        )
    return None  # mês ainda não publicado — UNKNOWN over guess
