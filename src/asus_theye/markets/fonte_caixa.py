# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: Loterias Caixa — Mega-Sena.

A Mega-Sena é o evento que mais brasileiro acompanha por semana, o resultado é
público minutos depois do sorteio e não muda mais. Isso a torna uma das poucas
fontes de entretenimento com qualidade de liquidação comparável à de um índice
oficial: número sorteado não se retifica.

O QUE NÃO COTAMOS, E POR QUÊ. "A Mega-Sena vai acumular?" é a pergunta óbvia e
está fora de uso aqui: nos 45 concursos lidos da própria API (3006 a 3050),
acumulou em **82,2%** deles. Um mercado que nasce em 82% viola a faixa de
exibição da casa (28..72¢) e não informa nada — todo mundo já sabe a resposta.
As três medidas abaixo foram escolhidas por ficarem, no mesmo histórico,
perto da máxima incerteza:

  soma das dezenas >= 184 (mediana)  -> 51,1%
  ganhadores da quina >= 41 (mediana) -> 53,3%
  quatro ou mais dezenas pares         -> 42,2%

PERÍODO É O DIA DO SORTEIO. A API é indexada por número de concurso, não por
data, então o conector lê o concurso corrente e só devolve valor se a
``dataApuracao`` for exatamente o dia pedido. Dia sem sorteio — ou sorteio que
ainda não aconteceu — é ``None`` (UNKNOWN), nunca um palpite sobre o concurso
errado.

RESSALVA DE PROCEDÊNCIA, dita na cara: este endpoint é o backend que alimenta
``loterias.caixa.gov.br`` e **não é uma API pública documentada**. A fonte legal
do resultado é o portal da Caixa; o JSON é espelho técnico, substituível. Se o
layout mudar, este módulo levanta em vez de adivinhar.
"""

from __future__ import annotations

import json
import re

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

URL_MEGASENA = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
MAX_BYTES = 400_000
TIMEOUT = 30

#: Dia do sorteio, ``aaaa-mm-dd``. Estrito: o dia é o que amarra o contrato ao
#: concurso, e uma data reformatada em silêncio ligaria o mercado a outro sorteio.
DIA_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")

#: Faixa de premiação da quina, como a Caixa a escreve.
FAIXA_QUINA = "5 acertos"


class FonteCaixaError(FonteError):
    """Resposta inesperada da Caixa. Sempre levanta — nunca degrada em valor."""


def _dia_br(dia: str) -> str:
    """``aaaa-mm-dd`` -> ``dd/mm/aaaa``, o formato que a Caixa publica."""
    if not isinstance(dia, str) or not DIA_RE.match(dia):
        raise FonteCaixaError(f"dia do sorteio em formato inesperado: {dia!r}")
    ano, mes, d = dia.split("-")
    return f"{d}/{mes}/{ano}"


def _concurso(dia: str, *, transport: Transport | None = None) -> dict | None:
    """Concurso da Mega-Sena apurado em ``dia``, ou ``None`` se ainda não houve."""
    esperado = _dia_br(dia)
    try:
        response = get_bytes(
            URL_MEGASENA,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteCaixaError(f"fonte inalcançável: {exc}") from exc
    if response.status != 200:
        raise FonteCaixaError(f"Caixa respondeu HTTP {response.status} em {URL_MEGASENA}")

    try:
        dados = json.loads(response.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FonteCaixaError(f"resposta da Caixa não é JSON válido ({exc})") from exc
    if not isinstance(dados, dict):
        raise FonteCaixaError(f"resposta da Caixa em formato inesperado: {type(dados).__name__}")
    if "dataApuracao" not in dados or "listaDezenas" not in dados:
        raise FonteCaixaError(f"resposta da Caixa sem os campos esperados: {sorted(dados)[:8]}")

    # O concurso corrente ainda não é o do dia pedido: o sorteio não aconteceu.
    if str(dados["dataApuracao"]).strip() != esperado:
        return None
    return dados


def _dezenas(concurso: dict) -> list[int]:
    bruto = concurso.get("listaDezenas")
    if not isinstance(bruto, list) or len(bruto) != 6:
        raise FonteCaixaError(f"esperava 6 dezenas sorteadas, veio {bruto!r}")
    try:
        dezenas = [int(str(d).strip()) for d in bruto]
    except ValueError as exc:
        raise FonteCaixaError(f"dezena não numérica no resultado: {bruto!r}") from exc
    if any(not 1 <= d <= 60 for d in dezenas):
        raise FonteCaixaError(f"dezena fora do volante 1..60: {dezenas!r}")
    if len(set(dezenas)) != 6:
        raise FonteCaixaError(f"dezena repetida no mesmo sorteio: {dezenas!r}")
    return dezenas


def soma_das_dezenas(dia: str, *, transport: Transport | None = None) -> float | None:
    """Soma das 6 dezenas sorteadas no concurso apurado em ``dia``."""
    concurso = _concurso(dia, transport=transport)
    if concurso is None:
        return None
    return float(sum(_dezenas(concurso)))


def dezenas_pares(dia: str, *, transport: Transport | None = None) -> float | None:
    """Quantas das 6 dezenas sorteadas são pares."""
    concurso = _concurso(dia, transport=transport)
    if concurso is None:
        return None
    return float(sum(1 for d in _dezenas(concurso) if d % 2 == 0))


def ganhadores_da_quina(dia: str, *, transport: Transport | None = None) -> float | None:
    """Número de apostas premiadas com 5 acertos no concurso apurado em ``dia``."""
    concurso = _concurso(dia, transport=transport)
    if concurso is None:
        return None
    faixas = concurso.get("listaRateioPremio")
    if not isinstance(faixas, list) or not faixas:
        raise FonteCaixaError(f"resultado sem as faixas de premiação: {faixas!r}")
    for faixa in faixas:
        if not isinstance(faixa, dict):
            raise FonteCaixaError(f"faixa de premiação em formato inesperado: {faixa!r}")
        if str(faixa.get("descricaoFaixa", "")).strip() == FAIXA_QUINA:
            ganhadores = faixa.get("numeroDeGanhadores")
            if isinstance(ganhadores, bool) or not isinstance(ganhadores, int):
                raise FonteCaixaError(f"número de ganhadores não inteiro: {ganhadores!r}")
            if ganhadores < 0:
                raise FonteCaixaError(f"número de ganhadores negativo: {ganhadores!r}")
            return float(ganhadores)
    raise FonteCaixaError(
        f"faixa {FAIXA_QUINA!r} não veio no resultado — a Caixa mudou os rótulos: "
        f"{[f.get('descricaoFaixa') for f in faixas]}"
    )
