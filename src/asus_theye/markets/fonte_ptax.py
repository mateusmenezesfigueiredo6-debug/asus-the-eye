# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: Banco Central do Brasil, série SGS 1 (PTAX venda diária).

Este é o terceiro conector de fonte oficial e segue o mesmo molde do conector
do BCB: consulta a fonte OFICIAL declarada pela área ``cambio`` e devolve o
último valor publicado dentro do mês de referência — ou ``None`` quando ainda
não existe publicação no mês. Nunca inventa: mês sem publicação é UNKNOWN.

A API é pública e sem chave: ``api.bcb.gov.br/dados/serie/bcdata.sgs.1``.
O transporte é injetável (``net.http.Transport``) para a suíte rodar offline.
"""

from __future__ import annotations

import calendar
import json

from asus_theye.net.http import HttpError, Transport, get_bytes

SERIE_PTAX = 1
URL_INTERVALO = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
    "?formato=json&dataInicial={data_inicial}&dataFinal={data_final}"
)
MAX_BYTES = 200_000
TIMEOUT = 30


class FontePTAXError(RuntimeError):
    """Resposta inesperada da fonte oficial. Sempre levanta — nunca degrada em valor."""


def _intervalo_mes(mes_referencia: str) -> tuple[str, str]:
    """Converte ``aaaa-mm`` em ``dd/mm/aaaa`` de início e fim do mês."""
    try:
        ano_txt, mes_txt = mes_referencia.split("-")
        ano, mes = int(ano_txt), int(mes_txt)
    except ValueError as exc:
        raise FontePTAXError(f"mes_referencia fora do formato aaaa-mm: {mes_referencia!r}") from exc
    if ano < 1 or not 1 <= mes <= 12:
        raise FontePTAXError(f"mes_referencia fora do formato aaaa-mm: {mes_referencia!r}")
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return f"01/{mes:02d}/{ano:04d}", f"{ultimo_dia:02d}/{mes:02d}/{ano:04d}"


def _ordem_data(data_bcb: str) -> tuple[int, int, int]:
    """Converte data do BCB (``dd/mm/aaaa``) para tupla ordenável (``aaaa, mm, dd``)."""
    try:
        dia_txt, mes_txt, ano_txt = data_bcb.split("/")
        return int(ano_txt), int(mes_txt), int(dia_txt)
    except ValueError as exc:
        raise FontePTAXError(f"data em formato inesperado do BCB: {data_bcb!r}") from exc


def ptax_venda_do_dia(dia: str, *, transport: Transport | None = None) -> float | None:
    """PTAX venda publicada no dia ``dia`` (``aaaa-mm-dd``).

    Devolve ``None`` quando o BCB não publicou naquele dia (fim de semana,
    feriado ou dia ainda em curso) — UNKNOWN, nunca chute. O mercado diário
    espera o dia útil seguinte em vez de inventar cotação.
    """
    try:
        ano, mes, d = (int(x) for x in dia.split("-"))
        data_bcb = f"{d:02d}/{mes:02d}/{ano:04d}"
    except (ValueError, AttributeError) as exc:
        raise FontePTAXError(f"dia fora do formato aaaa-mm-dd: {dia!r}") from exc
    return _ultimo_valor_no_intervalo(data_bcb, data_bcb, transport=transport)


def ptax_venda_fim_do_mes(mes_referencia: str, *, transport: Transport | None = None) -> float | None:
    """Última PTAX venda publicada no mês ``mes_referencia`` (``aaaa-mm``).

    Devolve ``None`` se o mês ainda não foi publicado (UNKNOWN, não chute).
    Levanta :class:`FontePTAXError` para resposta malformada ou HTTP != 200 —
    fonte com erro não é fonte com valor.
    """
    data_inicial, data_final = _intervalo_mes(mes_referencia)
    return _ultimo_valor_no_intervalo(data_inicial, data_final, transport=transport)


def _ultimo_valor_no_intervalo(
    data_inicial: str, data_final: str, *, transport: Transport | None = None
) -> float | None:
    """Último valor publicado no intervalo ``dd/mm/aaaa``. ``None`` se vazio."""
    url = URL_INTERVALO.format(serie=SERIE_PTAX, data_inicial=data_inicial, data_final=data_final)
    try:
        response = get_bytes(
            url, headers={"Accept": "application/json"}, timeout=TIMEOUT, max_bytes=MAX_BYTES, transport=transport
        )
    except HttpError as exc:
        raise FontePTAXError(f"fonte oficial inalcançável: {exc}") from exc
    if response.status != 200:
        raise FontePTAXError(f"fonte oficial respondeu HTTP {response.status} em {url}")

    try:
        pontos = json.loads(response.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FontePTAXError(f"resposta do BCB não é JSON válido ({exc})") from exc
    if not isinstance(pontos, list):
        raise FontePTAXError(f"resposta do BCB em formato inesperado: {type(pontos).__name__}")
    if not pontos:
        return None  # mês ainda sem publicação — UNKNOWN over guess

    ultimo_ponto: tuple[int, int, int] | None = None
    ultimo_valor: float | None = None
    for ponto in pontos:
        if not isinstance(ponto, dict) or "data" not in ponto or "valor" not in ponto:
            raise FontePTAXError(f"ponto em formato inesperado do BCB: {ponto!r}")
        data_ordenavel = _ordem_data(str(ponto["data"]))
        try:
            valor = float(str(ponto["valor"]).replace(",", "."))
        except ValueError as exc:
            raise FontePTAXError(f"valor não numérico do BCB: {ponto['valor']!r}") from exc
        if ultimo_ponto is None or data_ordenavel >= ultimo_ponto:
            ultimo_ponto, ultimo_valor = data_ordenavel, valor

    if ultimo_valor is None:  # pragma: no cover
        raise FontePTAXError("série do BCB sem valor utilizável")
    return ultimo_valor
