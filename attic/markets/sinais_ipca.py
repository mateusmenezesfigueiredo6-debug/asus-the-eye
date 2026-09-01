# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1 — sinais REAIS para o gerador WPAM: a pergunta do IPCA deixa o 0,50 cego.

O maior bloqueador de venda da categoria: todo mercado nascia em p = 0,50, o
limiar onde skill é indemonstrável. Este módulo alimenta o gerador
(:mod:`asus_theye.markets.gerador`) com evidência de fontes nomeadas e
GRATUITAS do próprio Banco Central:

1. **Focus/Olinda** — mediana das expectativas de mercado para o IPCA do mês
   (``ExpectativaMercadoMensais``, ~100 instituições, atualização semanal).
2. **IPCA-15** (SGS 7478) — a prévia oficial do próprio índice, quando já
   publicada para o mês. Reusa o conector genérico ``fonte_bcb.ipca_mensal``.

Método declarado (nenhum número sem método):

- Cada fonte disponível vira UM sinal com peso FIXO — Focus 20, IPCA-15 10
  (a prévia oficial pesa menos que o consenso porque cobre só metade do mês,
  mas ambos movem o prior de pseudo-contagem 10 do gerador).
- Direção: valor da fonte >= limiar do claim → "sim"; senão "nao". O critério
  é o MESMO do claim ("IPCA mensal >= limiar"), fonte e critério casados.
- Fonte indisponível (mês sem publicação) → SEM sinal daquela fonte. Nenhuma
  fonte → o gerador devolve exatamente 0,50 com ``max_uncertainty=True``
  (invariante do WPAM: sem evidência, nada de convicção inventada).
- Resposta malformada ou HTTP de erro → LEVANTA (:class:`SinaisError`), nunca
  degrada em palpite. Quem emite mercado decide o fallback (e ele é: emitir
  com prior honesto, dizendo por quê).
"""

from __future__ import annotations

import json
from urllib.parse import quote

from asus_theye.markets.fonte_bcb import FonteBCBError, ipca_mensal
from asus_theye.markets.gerador import Probabilidade, Sinal, gerar_probabilidade
from asus_theye.net.http import HttpError, Transport, get_bytes

SERIE_IPCA15 = 7478
PESO_FOCUS = 20.0
PESO_IPCA15 = 10.0
URL_FOCUS = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
    "ExpectativaMercadoMensais?%24filter={filtro}&%24orderby=Data%20desc&%24top=1"
    "&%24select=Data%2CMediana&%24format=json"
)
MAX_BYTES = 200_000
TIMEOUT = 30


class SinaisError(RuntimeError):
    """Fonte de sinal malformada ou fora do ar. Sempre levanta — sinal não se inventa."""


def _mes_olinda(mes_referencia: str) -> str:
    """``aaaa-mm`` → ``mm/aaaa`` (o formato de ``DataReferencia`` no Olinda)."""
    try:
        ano, mes = mes_referencia.split("-")
        if len(ano) != 4 or len(mes) != 2:
            raise ValueError(mes_referencia)
    except ValueError as exc:
        raise SinaisError(f"mes_referencia deve ser 'aaaa-mm', veio {mes_referencia!r}") from exc
    return f"{mes}/{ano}"


def mediana_focus_ipca(
    mes_referencia: str,
    *,
    transport: Transport | None = None,
) -> tuple[float, str] | None:
    """Mediana Focus mais recente para o IPCA de ``mes_referencia`` — ou ``None``.

    Devolve ``(mediana, data_do_boletim)``. ``None`` quando o Olinda não tem
    linha para o mês (UNKNOWN, não zero). Malformado/HTTP ruim levanta.
    """
    filtro = quote(f"Indicador eq 'IPCA' and DataReferencia eq '{_mes_olinda(mes_referencia)}'")
    url = URL_FOCUS.format(filtro=filtro)
    try:
        response = get_bytes(
            url, headers={"Accept": "application/json"}, timeout=TIMEOUT, max_bytes=MAX_BYTES, transport=transport
        )
    except HttpError as exc:
        raise SinaisError(f"Focus/Olinda inalcançável: {exc}") from exc
    if response.status != 200:
        raise SinaisError(f"Focus/Olinda respondeu HTTP {response.status}")
    try:
        corpo = json.loads(response.body.decode("utf-8"))
        linhas = corpo["value"]
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise SinaisError(f"resposta do Olinda em formato inesperado ({exc})") from exc
    if not isinstance(linhas, list):
        raise SinaisError(f"'value' do Olinda deveria ser lista, veio {type(linhas).__name__}")
    if not linhas:
        return None
    linha = linhas[0]
    try:
        return float(linha["Mediana"]), str(linha["Data"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SinaisError(f"linha do Olinda sem Mediana/Data utilizáveis: {linha!r}") from exc


def sinais_para_ipca(
    mes_referencia: str,
    limiar: float,
    *,
    transport: Transport | None = None,
) -> list[Sinal]:
    """Os sinais disponíveis HOJE para a pergunta 'IPCA de ``mes`` >= ``limiar``?'."""
    sinais: list[Sinal] = []

    focus = mediana_focus_ipca(mes_referencia, transport=transport)
    if focus is not None:
        mediana, boletim = focus
        sinais.append(
            Sinal(
                direcao="sim" if mediana >= limiar else "nao",
                peso=PESO_FOCUS,
                fonte=(
                    f"BCB Focus/Olinda ExpectativaMercadoMensais — mediana IPCA "
                    f"{mes_referencia}: {mediana:.2f}% (boletim {boletim}; criterio >= {limiar:.2f}%)"
                ),
            )
        )

    try:
        previa = ipca_mensal(mes_referencia, serie=SERIE_IPCA15, transport=transport)
    except FonteBCBError as exc:
        raise SinaisError(f"IPCA-15 (SGS {SERIE_IPCA15}) com resposta inválida: {exc}") from exc
    if previa is not None:
        sinais.append(
            Sinal(
                direcao="sim" if previa >= limiar else "nao",
                peso=PESO_IPCA15,
                fonte=(
                    f"BCB SGS {SERIE_IPCA15} (IPCA-15, prévia oficial) — "
                    f"{mes_referencia}: {previa:.2f}% (criterio >= {limiar:.2f}%)"
                ),
            )
        )

    return sinais


def probabilidade_para_ipca(
    mes_referencia: str,
    limiar: float,
    *,
    transport: Transport | None = None,
) -> Probabilidade:
    """Probabilidade WPAM da pergunta do mês, com proveniência completa.

    Sem nenhuma fonte disponível → exatamente 0,50 com ``max_uncertainty=True``
    (o invariante do gerador). É esta função que a emissão de mercados usa.
    """
    return gerar_probabilidade(sinais_para_ipca(mes_referencia, limiar, transport=transport))
