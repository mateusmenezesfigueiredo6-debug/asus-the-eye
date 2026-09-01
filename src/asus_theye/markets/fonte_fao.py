# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: FAO — Food Price Index (FFPI), commodities alimentares mensais.

POR QUE ESTA FONTE. O setor COMMODITIES precisa de um termômetro que qualquer
pessoa reconheça, e comida é a commodity que todo mundo sente antes de ler
qualquer índice. O FFPI é o indicador OFICIAL da FAO/ONU: mensal, gratuito, sem
chave e sem cota, série desde 1990-01, base 2014-2016=100, com o índice geral e
cinco subíndices (carnes, laticínios, cereais, óleos, açúcar). Um número por
mês, publicado pela mesma instituição há décadas — exatamente o perfil de fonte
que liquida contrato sem discussão.

TUDO ABAIXO FOI CONFERIDO AO VIVO EM 01/09/2026, não deduzido de documentação.

  Página oficial (é dela que sai o link do CSV):
    https://www.fao.org/worldfoodsituation/foodpricesindex/en/
    -> 200. Lista três arquivos: um xlsx mensal+anual (``ffpi-data-2026-08.xlsx``),
    um xlsx anual desde 1961, e o CSV mensal nominal — que é o que este conector lê.

  O CSV real:
    https://www.fao.org/media/docs/worldfoodsituationlibraries/default-document-library/food_price_indices_data.csv
    -> 200 tanto NA FORMA NUA quanto com o token de CMS que a página anexa
    (``?sfvrsn=523ebd2a_82&download=true``). Usamos a forma nua: ``sfvrsn`` é
    versão interna do Sitefinity e muda a cada publicação — um conector preso ao
    token quebraria todo mês por motivo nenhum.

  Layout conferido, linha a linha:
    linha 1: ``FAO Food Price Index`` (título, com cauda de ~60 vírgulas vazias)
    linha 2: ``2014-2016=100`` (a base do índice)
    linha 3: ``Date,Food Price Index,Meat,Dairy,Cereals,Oils,Sugar`` (cabeçalho)
    linha 4: só vírgulas (decorativa, vazia)
    linha 5+: dados, um mês por linha, de ``1990-01`` em diante
    Toda linha carrega a mesma cauda de campos vazios; o ``csv`` da stdlib lê a
    cauda como strings vazias e este módulo a ignora.

  Números conferidos no dado real:
    separador de campo: VÍRGULA. Decimal: PONTO — ``64.4``, ``44.59``, ``131.1``.
    Nada de vírgula decimal; se um valor vier com vírgula, o layout mudou e o
    conector LEVANTA em vez de adivinhar (ver ``_valor``).
    Último mês publicado em 01/09/2026: ``2026-07`` = 131.1.

DEFASAGEM DE ~UM MÊS É PARTE DO CONTRATO, NÃO DEFEITO. A FAO publica o mês M no
início de M+1 — e em 01/09/2026 agosto AINDA não estava no CSV, só julho. Mês
ausente é UNKNOWN (``None``), nunca zero: devolver 0.0 para mês não publicado
liquidaria "o índice caiu abaixo de X?" como SIM todo início de mês, contra um
número que não existe.

O arquivo real tem ordem de dezenas de KB (uma linha por mês desde 1990);
``MAX_BYTES`` de 4 MB é folga de sobra sem deixar passar um corpo absurdo.

O transporte é injetável (``net.http.Transport``) para a suíte rodar offline.
"""

from __future__ import annotations

import csv
import io
import re

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

#: Forma nua, sem o token ``sfvrsn`` do CMS — ver a nota do módulo. Conferida
#: ao vivo em 01/09/2026 (200, CSV íntegro). Constante para que uma mudança de
#: endereço da FAO seja um diff de uma linha, não uma caça ao literal.
URL_CSV = (
    "https://www.fao.org/media/docs/worldfoodsituationlibraries"
    "/default-document-library/food_price_indices_data.csv"
)

#: O CDN da FAO devolve 403 para o User-Agent padrão do urllib (medido em
#: 01/09/2026: sem UA → 403; qualquer UA identificado → 200). O coletor se
#: apresenta pelo nome, como um robô honesto faz — não finge ser navegador.
USER_AGENT = "asus-theye/1.0 (coleta mensal do indice publico FFPI)"
MAX_BYTES = 4_000_000
TIMEOUT = 60

COLUNA_DATA = "Date"
COLUNA_INDICE = "Food Price Index"
#: Os cinco subíndices, na ordem do cabeçalho real. Este conector só liquida o
#: índice geral, mas a validação de layout confere contra o cabeçalho inteiro
#: documentado — e quem for expor os subíndices amanhã já sabe os nomes exatos.
SUBINDICES = ("Meat", "Dairy", "Cereals", "Oils", "Sugar")

MES_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")

#: O índice histórico oscila entre ~35 e ~160 pontos (base 2014-2016=100).
#: Acima de 1000 não é recorde de preço de comida — é base, unidade ou layout
#: que mudou, e ninguém liquida contra isso sem olhar antes.
LIMITE_SUPERIOR = 1000.0

#: Assinaturas de arquivo binário que já chegaram no lugar de CSV em outras
#: fontes: zip/xlsx (``PK..``) e o OLE do xls antigo. A FAO publica xlsx na
#: mesma página — um link trocado no CMS entregaria planilha binária aqui.
ASSINATURAS_BINARIAS = (b"PK\x03\x04", b"\xd0\xcf\x11\xe0")


class FonteFAOError(FonteError):
    """Resposta inesperada da FAO. Sempre levanta — nunca degrada em valor."""


def _mes_valido(mes_referencia: str) -> str:
    if not isinstance(mes_referencia, str) or not MES_RE.fullmatch(mes_referencia):
        raise FonteFAOError(
            f"mês de referência em formato inesperado (esperado aaaa-mm): {mes_referencia!r}"
        )
    return mes_referencia


def _valor(bruto: object, contexto: str) -> float:
    """Índice como a FAO escreve: PONTO decimal (``131.1``), sem separador de milhar.

    Conferido no dado real em 01/09/2026 — ``64.4``, ``44.59``, ``131.1``. Se um
    valor vier com vírgula (um ``"131,1"`` entre aspas, por exemplo), isso é
    layout novo, e trocar vírgula por ponto às cegas poderia igualmente mascarar
    um separador de milhar. Não se adivinha: levanta.
    """
    texto = str(bruto).strip()
    if not texto:
        raise FonteFAOError(f"{contexto}: valor vazio no CSV da FAO — mês listado sem índice")
    if "," in texto:
        raise FonteFAOError(
            f"{contexto}: vírgula no valor {bruto!r} — a FAO usa ponto decimal "
            "(conferido em 01/09/2026); vírgula é layout novo, não se adivinha"
        )
    try:
        valor = float(texto)
    except ValueError as exc:
        raise FonteFAOError(f"{contexto}: valor não numérico na FAO: {bruto!r}") from exc
    if valor != valor or valor in (float("inf"), float("-inf")):
        raise FonteFAOError(f"{contexto}: valor NaN/Infinito na FAO: {bruto!r}")
    if valor <= 0:
        raise FonteFAOError(
            f"{contexto}: índice não-positivo ({valor}) — a base 2014-2016 é 100, zero não existe"
        )
    if valor >= LIMITE_SUPERIOR:
        raise FonteFAOError(
            f"{contexto}: índice {valor} acima de {LIMITE_SUPERIOR:g} pontos — "
            "base, unidade ou layout mudou; ninguém liquida contra isso sem olhar"
        )
    return valor


def _baixar(transport: Transport | None) -> bytes:
    try:
        resposta = get_bytes(
            URL_CSV,
            headers={"Accept": "text/csv", "User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteFAOError(f"fonte oficial inalcançável: {exc}") from exc
    if resposta.status != 200:
        raise FonteFAOError(f"a FAO respondeu HTTP {resposta.status} em {URL_CSV}")
    return resposta.body


def _decodificar(corpo: bytes) -> str:
    """UTF-8 ou nada — com diagnóstico próprio para planilha binária.

    A página da FAO oferece xlsx AO LADO do CSV; se o CMS trocar o link, o corpo
    chega começando com a assinatura zip (``PK..``) ou OLE (xls antigo). Esses
    bytes até decodificam parcialmente como UTF-8, então o erro genérico de
    decodificação NÃO os pega — a assinatura é conferida antes, de propósito.
    """
    for assinatura in ASSINATURAS_BINARIAS:
        if corpo.startswith(assinatura):
            raise FonteFAOError(
                "a FAO devolveu planilha binária (xlsx/xls) no lugar do CSV — "
                f"o corpo começa com {assinatura!r}; o link do CMS deve ter trocado de arquivo"
            )
    try:
        return corpo.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FonteFAOError(f"o corpo da FAO não decodifica em UTF-8 ({exc}) — não é o CSV documentado") from exc


def _serie_do_texto(texto: str) -> dict[str, float]:
    """Parse do layout conferido ao vivo: título, base, cabeçalho, linha vazia, dados."""
    linhas = list(csv.reader(io.StringIO(texto)))

    posicao_cabecalho = None
    cabecalho: list[str] = []
    for posicao, linha in enumerate(linhas):
        if linha and linha[0].strip() == COLUNA_DATA:
            posicao_cabecalho = posicao
            cabecalho = [celula.strip() for celula in linha]
            break
    if posicao_cabecalho is None:
        raise FonteFAOError(
            f"CSV da FAO sem a linha de cabeçalho que começa com {COLUNA_DATA!r} — o layout mudou"
        )
    if COLUNA_INDICE not in cabecalho:
        raise FonteFAOError(
            f"CSV da FAO sem a coluna {COLUNA_INDICE!r} — o layout mudou: "
            f"{[c for c in cabecalho if c]}"
        )
    coluna = cabecalho.index(COLUNA_INDICE)

    serie: dict[str, float] = {}
    for numero, linha in enumerate(linhas[posicao_cabecalho + 1:], start=posicao_cabecalho + 2):
        if not any(celula.strip() for celula in linha):
            continue  # a linha decorativa sob o cabeçalho — conferida ao vivo
        mes = linha[0].strip()
        if not MES_RE.fullmatch(mes):
            raise FonteFAOError(
                f"linha {numero} do CSV da FAO não começa com mês aaaa-mm: {linha[0]!r} — "
                "rodapé ou layout novo; não se ignora linha em silêncio"
            )
        if len(linha) <= coluna:
            raise FonteFAOError(
                f"linha {numero} ({mes}) do CSV da FAO tem só {len(linha)} colunas — "
                f"a coluna {COLUNA_INDICE!r} (posição {coluna + 1}) não existe nela"
            )
        if mes in serie:
            raise FonteFAOError(
                f"o mês {mes} aparece repetido no CSV da FAO — ambíguo, não liquida"
            )
        serie[mes] = _valor(linha[coluna], f"{COLUNA_INDICE} em {mes}")
    if not serie:
        raise FonteFAOError("CSV da FAO sem nenhuma linha de dado abaixo do cabeçalho")
    return serie


def serie_ffpi(*, transport: Transport | None = None) -> dict[str, float]:
    """A série mensal completa do índice geral: mapa ``aaaa-mm`` -> pontos.

    Cada valor passou pela validação de ``_valor`` (numérico, positivo, ponto
    decimal, abaixo do teto de sanidade) e cada mês aparece uma única vez —
    duplicata levanta em vez de sobrescrever calada. É desta série que sai
    qualquer limiar da casa: mediana lida da PRÓPRIA fonte, nunca escolhida a
    dedo, verificável por qualquer um que baixe o mesmo CSV.
    """
    return _serie_do_texto(_decodificar(_baixar(transport)))


def indice_no_mes(mes_referencia: str, *, transport: Transport | None = None) -> float | None:
    """O Food Price Index (índice geral) do mês ``mes_referencia`` (``aaaa-mm``).

    Devolve ``None`` quando o mês ainda não está no CSV — a FAO publica o mês M
    no início de M+1 (em 01/09/2026, julho era o último; agosto, ausente). Isso
    é UNKNOWN, nunca zero: ausência de publicação não é índice zerado.
    """
    mes = _mes_valido(mes_referencia)
    return serie_ffpi(transport=transport).get(mes)
