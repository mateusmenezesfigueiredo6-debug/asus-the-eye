# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: CISA KEV — vulnerabilidades exploradas conhecidas.

POR QUE ESTA FONTE. O setor CYBER precisa de um desfecho que qualquer pessoa
possa conferir baixando o mesmo arquivo — e o catálogo KEV (Known Exploited
Vulnerabilities) da CISA é exatamente isso: a agência de cibersegurança do
governo dos EUA mantém UM JSON público, sem chave e sem cota, listando cada
CVE com exploração confirmada em campo e a data em que entrou no catálogo.
"Quantos CVEs entram no KEV em setembro?" é um contrato que liquida contra um
documento oficial, enumerável e datado — não contra manchete.

LICENÇA. Dado público do governo dos EUA: a própria CISA publica o feed para
consumo automatizado e o distribui como dado aberto, sem restrição de chave
ou de cadastro.

TUDO ABAIXO FOI CONFERIDO AO VIVO EM 01/09/2026, não deduzido de documentação.

  O feed:
    https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
    -> 200, ~1-2 MB. Chaves de topo: title, catalogVersion ("2026.09.01"),
    dateReleased ("2026-09-01T19:22:46.2162Z"), count (1687) e
    vulnerabilities[] — count declara o tamanho da lista.

  Uma entrada real (CVE-2026-82078):
    cveID="CVE-2026-82078", vendorProject, product, vulnerabilityName,
    dateAdded="2026-08-31" (formato aaaa-mm-dd, SEM hora), shortDescription,
    requiredAction, dueDate, knownRansomwareCampaignUse, notes, cwes[].

ZERO AQUI É LEGÍTIMO — e isso é diferente das séries temporais desta casa.
O KEV é um catálogo completo e enumerável: baixar o documento é ver TODAS as
entradas que existem. Um mês sem nenhuma entrada significa de fato "nenhum CVE
adicionado naquele mês", não "a fonte ainda não publicou". A mesma lógica vale
para mês futuro: a contagem é do que EXISTE no catálogo na hora da leitura —
e o critério do contrato tem de dizer isso, porque a contagem de um mês ainda
aberto pode crescer até o mês fechar. UNKNOWN over guess continua valendo onde
importa: documento malformado, HTTP fora do esperado, lista ausente ou entrada
sem data LEVANTAM ``FonteCISAError`` — nunca degradam em palpite.

O transporte é injetável (``net.http.Transport``) para a suíte rodar offline.
"""

from __future__ import annotations

import json
import re

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

URL_KEV = (
    "https://www.cisa.gov/sites/default/files/feeds"
    "/known_exploited_vulnerabilities.json"
)
#: O feed media ~1-2 MB em 01/09/2026; 8 MB dá folga para anos de crescimento
#: sem deixar passar um corpo absurdo (``max_bytes`` é obrigatório na casa).
MAX_BYTES = 8_000_000
TIMEOUT = 60

MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
#: ``dateAdded`` como a CISA escreve: aaaa-mm-dd, sem hora. Conferido ao vivo.
DATA_ADICAO_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


class FonteCISAError(FonteError):
    """Resposta inesperada da CISA. Sempre levanta — nunca degrada em valor."""


def _mes_valido(mes_referencia: str) -> str:
    if not isinstance(mes_referencia, str) or not MES_RE.match(mes_referencia):
        raise FonteCISAError(
            f"mês de referência em formato inesperado (esperado aaaa-mm): {mes_referencia!r}"
        )
    return mes_referencia


def catalogo_kev(*, transport: Transport | None = None) -> dict:
    """O catálogo KEV inteiro, validado — nunca um documento parcial.

    Levanta ``FonteCISAError`` quando o HTTP não é 200, o corpo não é JSON,
    o topo não é um objeto, ``vulnerabilities`` está ausente ou não é lista,
    ou ``count`` declara um tamanho diferente do que a lista traz — este
    último caso significa documento truncado ou inconsistente, e liquidar
    contra ele seria contar um catálogo que a própria CISA diz estar errado.
    """
    try:
        resposta = get_bytes(
            URL_KEV,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteCISAError(f"fonte oficial inalcançável: {exc}") from exc
    if resposta.status != 200:
        raise FonteCISAError(f"CISA respondeu HTTP {resposta.status} em {URL_KEV}")

    try:
        documento = json.loads(resposta.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FonteCISAError(f"catálogo KEV não é JSON válido ({exc})") from exc
    if not isinstance(documento, dict):
        raise FonteCISAError(
            f"catálogo KEV não é um objeto JSON: veio {type(documento).__name__}"
        )

    vulnerabilidades = documento.get("vulnerabilities")
    if not isinstance(vulnerabilidades, list):
        raise FonteCISAError(
            f"catálogo KEV sem a lista 'vulnerabilities' — o layout mudou: {sorted(documento)}"
        )

    declarado = documento.get("count")
    if isinstance(declarado, int) and declarado != len(vulnerabilidades):
        raise FonteCISAError(
            f"catálogo KEV declara count={declarado} mas traz "
            f"{len(vulnerabilidades)} entradas — documento inconsistente"
        )
    return documento


def contagem_kev_no_mes(mes_referencia: str, *, transport: Transport | None = None) -> int:
    """Quantos CVEs entraram no KEV com ``dateAdded`` dentro de ``aaaa-mm``.

    Zero é resposta legítima: o catálogo é completo e enumerável, então mês
    sem entrada (inclusive mês futuro) conta 0 — é a contagem do que EXISTE
    no catálogo na hora da leitura, como declara o cabeçalho do módulo. Já
    entrada sem ``dateAdded`` ou com data fora de aaaa-mm-dd LEVANTA: uma
    entrada que não dá para incluir nem excluir honestamente contaminaria
    a contagem em silêncio.
    """
    mes = _mes_valido(mes_referencia)
    documento = catalogo_kev(transport=transport)

    prefixo = f"{mes}-"
    total = 0
    for entrada in documento["vulnerabilities"]:
        if not isinstance(entrada, dict):
            raise FonteCISAError(f"entrada não-objeto no catálogo KEV: {entrada!r}")
        data = str(entrada.get("dateAdded", "")).strip()
        if not DATA_ADICAO_RE.match(data):
            raise FonteCISAError(
                f"dateAdded fora do formato aaaa-mm-dd no catálogo KEV: {data!r} "
                f"(cveID={entrada.get('cveID')!r})"
            )
        if data.startswith(prefixo):
            total += 1
    return total
