# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sinais reais para o gerador WPAM: a pergunta do JUROS deixa o 0,50 cego.

Alimenta o gerador (:mod:`asus_theye.markets.gerador`) com evidência de fontes
nomeadas e GRATUITAS do próprio Banco Central:

1. **Focus/Olinda** — mediana das expectativas de mercado para a Selic do mês
   (``ExpectativaMercadoMensais``, ~100 instituições, atualização semanal).
2. **Meta Selic** (SGS 432) — a meta oficial publicada pelo BCB para o mês,
   quando já disponível. Reusa o conector ``fonte_selic.selic_meta``.

Método declarado (nenhum número sem método):

- Cada fonte disponível vira UM sinal com peso FIXO — Focus 20, SGS-432 10.
- Direção: valor da fonte >= limiar do claim → "sim"; senão "nao".
- Fonte indisponível → SEM sinal daquela fonte. Nenhuma fonte → o gerador
  devolve exatamente 0,50 com ``max_uncertainty=True``.
- Resposta malformada ou HTTP de erro → LEVANTA (:class:`SinaisJurosError`).
"""

from __future__ import annotations

import json
from urllib.parse import quote

from asus_theye.markets.fonte_selic import FonteSelicError, selic_meta
from asus_theye.markets.gerador import Probabilidade, Sinal, gerar_probabilidade
from asus_theye.net.http import HttpError, Transport, get_bytes

PESO_FOCUS = 20.0
PESO_SELIC = 10.0
URL_FOCUS = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
    "ExpectativaMercadoMensais?%24filter={filtro}&%24orderby=Data%20desc&%24top=1"
    "&%24select=Data%2CMediana&%24format=json"
)
MAX_BYTES = 200_000
TIMEOUT = 30


class SinaisJurosError(RuntimeError):
    """Fonte de sinal malformada ou fora do ar. Sempre levanta — sinal não se inventa."""


def _mes_olinda(mes_referencia: str) -> str:
    """``aaaa-mm`` → ``mm/aaaa`` (o formato de ``DataReferencia`` no Olinda)."""
    try:
        ano, mes = mes_referencia.split("-")
        if len(ano) != 4 or len(mes) != 2:
            raise ValueError(mes_referencia)
    except ValueError as exc:
        raise SinaisJurosError(f"mes_referencia deve ser 'aaaa-mm', veio {mes_referencia!r}") from exc
    return f"{mes}/{ano}"


def mediana_focus_selic(
    mes_referencia: str,
    *,
    transport: Transport | None = None,
) -> tuple[float, str] | None:
    """Mediana Focus mais recente para a Selic de ``mes_referencia`` — ou ``None``.

    Devolve ``(mediana, data_do_boletim)``. ``None`` quando o Olinda não tem
    linha para o mês (UNKNOWN, não zero). Malformado/HTTP ruim levanta.
    """
    filtro = quote(f"Indicador eq 'Selic' and DataReferencia eq '{_mes_olinda(mes_referencia)}'")
    url = URL_FOCUS.format(filtro=filtro)
    try:
        response = get_bytes(
            url,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise SinaisJurosError(f"Focus/Olinda inalcançável: {exc}") from exc
    if response.status != 200:
        raise SinaisJurosError(f"Focus/Olinda respondeu HTTP {response.status}")
    try:
        corpo = json.loads(response.body.decode("utf-8"))
        linhas = corpo["value"]
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise SinaisJurosError(f"resposta do Olinda em formato inesperado ({exc})") from exc
    if not isinstance(linhas, list):
        raise SinaisJurosError(f"'value' do Olinda deveria ser lista, veio {type(linhas).__name__}")
    if not linhas:
        return None
    linha = linhas[0]
    try:
        return float(linha["Mediana"]), str(linha["Data"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SinaisJurosError(f"linha do Olinda sem Mediana/Data utilizáveis: {linha!r}") from exc


def sinais_para_juros(
    mes_referencia: str,
    limiar: float,
    *,
    transport: Transport | None = None,
) -> list[Sinal]:
    """Os sinais disponíveis HOJE para a pergunta 'Selic de ``mes`` >= ``limiar``?'."""
    sinais: list[Sinal] = []

    focus = mediana_focus_selic(mes_referencia, transport=transport)
    if focus is not None:
        mediana, boletim = focus
        sinais.append(
            Sinal(
                direcao="sim" if mediana >= limiar else "nao",
                peso=PESO_FOCUS,
                fonte=(
                    f"BCB Focus/Olinda ExpectativaMercadoMensais — mediana Selic "
                    f"{mes_referencia}: {mediana:.2f}% a.a. (boletim {boletim}; criterio >= {limiar:.2f}%)"
                ),
            )
        )

    try:
        meta = selic_meta(mes_referencia, transport=transport)
    except FonteSelicError as exc:
        raise SinaisJurosError(f"Selic meta (SGS 432) com resposta inválida: {exc}") from exc
    if meta is not None:
        sinais.append(
            Sinal(
                direcao="sim" if meta >= limiar else "nao",
                peso=PESO_SELIC,
                fonte=(
                    f"BCB SGS 432 (meta Selic oficial) — {mes_referencia}: {meta:.2f}% a.a. (criterio >= {limiar:.2f}%)"
                ),
            )
        )

    return sinais


def probabilidade_para_juros(
    mes_referencia: str,
    limiar: float,
    *,
    transport: Transport | None = None,
) -> Probabilidade:
    """Probabilidade WPAM da pergunta de juros do mês, com proveniência completa.

    Sem nenhuma fonte disponível → exatamente 0,50 com ``max_uncertainty=True``.
    """
    return gerar_probabilidade(sinais_para_juros(mes_referencia, limiar, transport=transport))
