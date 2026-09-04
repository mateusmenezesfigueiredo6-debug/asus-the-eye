# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: ClinicalTrials.gov — registro de ensaios clínicos.

POR QUE ESTA FONTE. O setor BIOTECNOLOGIA precisa de um desfecho que qualquer
pessoa possa conferir consultando o mesmo registro — e o ClinicalTrials.gov é
exatamente isso: o registro oficial de ensaios clínicos mantido pela NLM/NIH
(governo dos EUA), com API v2 pública, sem chave e sem cadastro. "Quantos
estudos com início em setembro têm sítio no Brasil?" é um contrato que liquida
contra um registro oficial, consultável e datado — não contra manchete.

LICENÇA. Dado público do governo dos EUA: a própria NLM publica a API v2 para
consumo automatizado, sem chave, sem cota declarada e sem cadastro.

TUDO ABAIXO FOI CONFERIDO AO VIVO EM 02/09/2026, não deduzido de documentação.

  A consulta (doc em https://clinicaltrials.gov/data-api/api):
    https://clinicaltrials.gov/api/v2/studies
      ?query.locn=Brazil
      &filter.advanced=AREA[StartDate]RANGE[2026-08-01,2026-08-31]
      &countTotal=true&pageSize=1
    -> 200, JSON com chaves de topo: totalCount, studies, nextPageToken.
    Em 02/09/2026 essa consulta exata devolveu totalCount=46. O mesmo 46 veio
    com os colchetes e a vírgula percent-encoded (%5B %5D %2C) — que é como
    ``urllib.parse.urlencode`` escreve, e como este módulo monta a URL.

  countTotal=true faz a API declarar o total no campo ``totalCount``;
  pageSize=1 evita baixar páginas de estudos que não usamos — só o total
  interessa. Cada entrada de ``studies`` traz protocolSection/derivedSection/
  hasResults (conferido ao vivo), mas este conector não as consome.

AVISO DA FONTE — E POR QUE O DESENHO DO MERCADO PRECISA DE FOLGA. StartDate no
registro pode ser ANTECIPADO: patrocinadores registram estudos com data de
início futura ("anticipated"), que depois muda ou nem se confirma. E registros
chegam com ATRASO: um estudo que começou em agosto pode só aparecer (ou só
ganhar StartDate de agosto) semanas depois. Consequência: a contagem de um mês
NÃO é estável no fim do mês — ela só assenta semanas depois. O contrato do
mercado tem de declarar isso e fixar deadline de liquidação com folga (isto é
para o DESENHO do mercado citar; o conector só conta o que o registro devolve
NA HORA DA LEITURA).

ZERO AQUI É LEGÍTIMO como resposta da consulta: countTotal=true declara o
total, e um mês/país sem estudo registrado conta 0 de verdade — sujeito ao
aviso acima sobre quando essa contagem assenta. UNKNOWN over guess continua
valendo onde importa: HTTP fora de 200, corpo que não é JSON, topo que não é
objeto, ``totalCount`` ausente ou que não é inteiro LEVANTAM
``FonteClinicalTrialsError`` — nunca degradam em palpite.

O transporte é injetável (``net.http.Transport``) para a suíte rodar offline.
"""

from __future__ import annotations

import calendar
import json
import re
from urllib.parse import urlencode

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

URL_ESTUDOS = "https://clinicaltrials.gov/api/v2/studies"
#: A resposta com pageSize=1 media dezenas de KB em 02/09/2026; 2 MB dá folga
#: larga sem deixar passar um corpo absurdo (``max_bytes`` é obrigatório na casa).
MAX_BYTES = 2_000_000
TIMEOUT = 60
#: Só o ``totalCount`` interessa — 1 é o menor pageSize que a API aceita.
PAGE_SIZE = 1
#: Sintaxe de filtro conferida ao vivo em 02/09/2026 (doc: /data-api/api).
FILTRO_START_DATE = "AREA[StartDate]RANGE[{inicio},{fim}]"

MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class FonteClinicalTrialsError(FonteError):
    """Resposta inesperada do ClinicalTrials.gov. Sempre levanta — nunca degrada em valor."""


def _mes_valido(mes_referencia: str) -> str:
    if not isinstance(mes_referencia, str) or not MES_RE.match(mes_referencia):
        raise FonteClinicalTrialsError(
            f"mês de referência em formato inesperado (esperado aaaa-mm): {mes_referencia!r}"
        )
    return mes_referencia


def _pais_valido(pais: str) -> str:
    if not isinstance(pais, str) or not pais.strip():
        raise FonteClinicalTrialsError(f"país vazio ou em formato inesperado: {pais!r}")
    return pais.strip()


def _url_contagem(mes: str, pais: str) -> str:
    """URL exata da consulta — o intervalo cobre do dia 01 ao último dia do mês.

    ``calendar.monthrange`` dá o último dia (28/29/30/31) sem aritmética
    manual; ``urlencode`` escreve colchetes e vírgula percent-encoded, forma
    conferida ao vivo em 02/09/2026 com o mesmo ``totalCount`` da forma crua.
    """
    ano, numero_mes = int(mes[:4]), int(mes[5:7])
    ultimo_dia = calendar.monthrange(ano, numero_mes)[1]
    filtro = FILTRO_START_DATE.format(inicio=f"{mes}-01", fim=f"{mes}-{ultimo_dia:02d}")
    consulta = urlencode(
        {
            "query.locn": pais,
            "filter.advanced": filtro,
            "countTotal": "true",
            "pageSize": PAGE_SIZE,
        }
    )
    return f"{URL_ESTUDOS}?{consulta}"


def contagem_estudos_no_mes(
    mes_referencia: str, *, pais: str = "Brazil", transport: Transport | None = None
) -> int:
    """Quantos estudos o registro declara com StartDate dentro de ``aaaa-mm`` e sítio no país.

    É a contagem que o registro devolve NA HORA DA LEITURA (``totalCount`` com
    ``countTotal=true``). Zero é resposta legítima da consulta — mas, como o
    cabeçalho do módulo avisa, StartDate pode ser antecipado e registros chegam
    com atraso, então a contagem de um mês só assenta semanas depois do mês
    fechar; o deadline com folga é responsabilidade do desenho do mercado.
    ``totalCount`` ausente, não-inteiro ou negativo LEVANTA: um total que não
    dá para ler honestamente não pode virar contagem em silêncio.
    """
    mes = _mes_valido(mes_referencia)
    url = _url_contagem(mes, _pais_valido(pais))

    try:
        resposta = get_bytes(
            url,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteClinicalTrialsError(f"fonte oficial inalcançável: {exc}") from exc
    if resposta.status != 200:
        raise FonteClinicalTrialsError(
            f"ClinicalTrials.gov respondeu HTTP {resposta.status} em {url}"
        )

    try:
        documento = json.loads(resposta.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FonteClinicalTrialsError(f"resposta não é JSON válido ({exc})") from exc
    if not isinstance(documento, dict):
        raise FonteClinicalTrialsError(
            f"resposta não é um objeto JSON: veio {type(documento).__name__}"
        )

    total = documento.get("totalCount")
    if total is None:
        raise FonteClinicalTrialsError(
            f"resposta sem 'totalCount' — countTotal=true não foi honrado "
            f"ou o layout mudou: {sorted(documento)}"
        )
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise FonteClinicalTrialsError(
            f"'totalCount' não é um inteiro não-negativo: {total!r}"
        )
    return total
