# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sinais reais para o gerador WPAM: a pergunta do CÂMBIO deixa o 0,50 cego.

Alimenta o gerador (:mod:`asus_theye.markets.gerador`) com evidência de fontes
nomeadas e GRATUITAS do próprio Banco Central:

1. **Focus/Olinda** — mediana das expectativas de mercado para o câmbio (USD)
   do mês (``ExpectativaMercadoMensais``, ~100 instituições, atualização semanal).
2. **PTAX venda** (SGS 1) — o último valor publicado pelo BCB no mês, quando
   já disponível. Reusa o conector ``fonte_ptax.ptax_venda_fim_do_mes``.

Método declarado (nenhum número sem método):

- Cada fonte disponível vira UM sinal com peso FIXO — Focus 20, PTAX 10.
- Direção: valor da fonte >= limiar do claim → "sim"; senão "nao".
- Fonte indisponível → SEM sinal daquela fonte. Nenhuma fonte → o gerador
  devolve exatamente 0,50 com ``max_uncertainty=True``.
- Resposta malformada ou HTTP de erro → LEVANTA (:class:`SinaisCambioError`).
"""

from __future__ import annotations

import json
from urllib.parse import quote

from asus_theye.markets.fonte_ptax import FontePTAXError, ptax_venda_fim_do_mes
from asus_theye.markets.gerador import Probabilidade, Sinal, gerar_probabilidade
from asus_theye.net.http import HttpError, Transport, get_bytes

PESO_FOCUS = 20.0
PESO_PTAX = 10.0
URL_FOCUS = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
    "ExpectativaMercadoMensais?%24filter={filtro}&%24orderby=Data%20desc&%24top=1"
    "&%24select=Data%2CMediana&%24format=json"
)
MAX_BYTES = 200_000
TIMEOUT = 30


class SinaisCambioError(RuntimeError):
    """Fonte de sinal malformada ou fora do ar. Sempre levanta — sinal não se inventa."""


def _mes_corrente() -> str:
    """Mês corrente em UTC — a janela onde a PTAX vigente de fato existe."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m")


def _mes_olinda(mes_referencia: str) -> str:
    """``aaaa-mm`` → ``mm/aaaa`` (o formato de ``DataReferencia`` no Olinda)."""
    try:
        ano, mes = mes_referencia.split("-")
        if len(ano) != 4 or len(mes) != 2:
            raise ValueError(mes_referencia)
    except ValueError as exc:
        raise SinaisCambioError(f"mes_referencia deve ser 'aaaa-mm', veio {mes_referencia!r}") from exc
    return f"{mes}/{ano}"


def mediana_focus_cambio(
    mes_referencia: str,
    *,
    transport: Transport | None = None,
) -> tuple[float, str] | None:
    """Mediana Focus mais recente para o câmbio (USD) de ``mes_referencia`` — ou ``None``.

    Devolve ``(mediana, data_do_boletim)``. ``None`` quando o Olinda não tem
    linha para o mês (UNKNOWN, não zero). Malformado/HTTP ruim levanta.
    """
    filtro = quote(f"Indicador eq 'Câmbio' and DataReferencia eq '{_mes_olinda(mes_referencia)}'")
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
        raise SinaisCambioError(f"Focus/Olinda inalcançável: {exc}") from exc
    if response.status != 200:
        raise SinaisCambioError(f"Focus/Olinda respondeu HTTP {response.status}")
    try:
        corpo = json.loads(response.body.decode("utf-8"))
        linhas = corpo["value"]
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise SinaisCambioError(f"resposta do Olinda em formato inesperado ({exc})") from exc
    if not isinstance(linhas, list):
        raise SinaisCambioError(f"'value' do Olinda deveria ser lista, veio {type(linhas).__name__}")
    if not linhas:
        return None
    linha = linhas[0]
    try:
        return float(linha["Mediana"]), str(linha["Data"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SinaisCambioError(f"linha do Olinda sem Mediana/Data utilizáveis: {linha!r}") from exc


def sinais_para_cambio(
    mes_referencia: str,
    limiar: float,
    *,
    transport: Transport | None = None,
) -> list[Sinal]:
    """Os sinais disponíveis HOJE para a pergunta 'PTAX de ``mes`` >= ``limiar``?'."""
    sinais: list[Sinal] = []

    focus = mediana_focus_cambio(mes_referencia, transport=transport)
    if focus is not None:
        mediana, boletim = focus
        sinais.append(
            Sinal(
                direcao="sim" if mediana >= limiar else "nao",
                peso=PESO_FOCUS,
                fonte=(
                    f"BCB Focus/Olinda ExpectativaMercadoMensais — mediana Câmbio "
                    f"{mes_referencia}: R$ {mediana:.2f} (boletim {boletim}; criterio >= R$ {limiar:.2f})"
                ),
            )
        )

    # A PTAX do MÊS-ALVO não serve como sinal, por dois motivos. Para um mês
    # futuro ela não existe — a API devolve 404, que é o caso NORMAL de um
    # mercado aberto, não um erro. E se existisse, seria a própria resposta:
    # usar o desfecho como insumo da previsão é circular. O sinal legítimo é a
    # PTAX vigente HOJE, que é informação disponível no momento da aposta.
    try:
        ptax = ptax_venda_fim_do_mes(_mes_corrente(), transport=transport)
    except FontePTAXError:
        # fonte indisponível é AUSÊNCIA DE SINAL, nunca erro fatal: um mercado
        # aberto não pode deixar de ser precificado porque uma das fontes falhou
        ptax = None
    if ptax is not None:
        sinais.append(
            Sinal(
                direcao="sim" if ptax >= limiar else "nao",
                peso=PESO_PTAX,
                fonte=(
                    f"BCB SGS 1 (PTAX venda vigente, {_mes_corrente()}) — "
                    f"R$ {ptax:.4f} (criterio do claim {mes_referencia}: >= R$ {limiar:.2f})"
                ),
            )
        )

    return sinais


def probabilidade_para_cambio(
    mes_referencia: str,
    limiar: float,
    *,
    transport: Transport | None = None,
) -> Probabilidade:
    """Probabilidade WPAM da pergunta de câmbio do mês, com proveniência completa.

    Sem nenhuma fonte disponível → exatamente 0,50 com ``max_uncertainty=True``.
    """
    return gerar_probabilidade(sinais_para_cambio(mes_referencia, limiar, transport=transport))
