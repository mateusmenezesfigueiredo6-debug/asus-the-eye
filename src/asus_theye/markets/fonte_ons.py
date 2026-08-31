# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: ONS — carga de energia diária por subsistema.

POR QUE ESTA FONTE, E POR QUE AGORA. O ativo vendável desta casa é a série de
acerto medido, e ela só cresce quando um contrato LIQUIDA. Em 30/08/2026 o
catálogo tinha 33 mercados e **1 liquidado** — porque quase tudo vence uma vez
por mês (IPCA, bandeira, INPC). Um contrato de carga diária liquida ~30 vezes
no tempo em que um de IPCA liquida uma. Não é "mais um setor": é a prova
acumulando trinta vezes mais rápido, com o mesmo esforço de engenharia.

TUDO ABAIXO FOI CONFERIDO AO VIVO EM 31/08/2026, não deduzido de documentação.

  Catálogo CKAN do ONS:
    https://dados.ons.org.br/api/3/action/package_search?q=carga  -> 200
    16 conjuntos; o que interessa é "Carga de Energia Diária", com um CSV por
    ano em bucket S3 público — sem chave, sem OAuth, sem cota.

  O arquivo do ciclo corrente:
    .../dataset/carga_energia_di/CARGA_ENERGIA_2026.csv  -> 200, 39.312 bytes
    cabeçalho: id_subsistema;nom_subsistema;din_instante;val_cargaenergiamwmed
    última linha em 31/08: 2026-08-28 (defasagem de ~3 dias)

  Medianas de 2026 (240 dias por subsistema), que são o limiar da casa:
    SE  43.883,9 MWmed   ·   NE  13.522,9   ·   S  14.155,6   ·   N  8.385,6

DEFASAGEM DE TRÊS DIAS É PARTE DO CONTRATO, NÃO DEFEITO. O ONS publica a carga
verificada alguns dias depois do fato. Um contrato sobre "a carga de amanhã"
liquidaria só três dias depois de amanhã — e isso tem de estar escrito no
critério, senão alguém abre um chamado achando que a fonte quebrou. É o mesmo
princípio da assinatura do TSE: declarar a limitação em vez de escondê-la.

ROTA REPROVADA, registrada para ninguém tentar de novo:
    integra.ons.org.br/api/energiaagora/get/carga -> 302 e depois 204 (vazio).
    É a API do painel "Energia Agora", pensada para o navegador do site. Não
    serve para liquidar: 204 não distingue "não há dado" de "não entendi".

O transporte é injetável (``net.http.Transport``) para a suíte rodar offline.
"""

from __future__ import annotations

import csv
import io
import re
import statistics

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

URL_CARGA_DIARIA = (
    "https://ons-aws-prod-opendata.s3.amazonaws.com"
    "/dataset/carga_energia_di/CARGA_ENERGIA_{ano}.csv"
)
MAX_BYTES = 8_000_000
TIMEOUT = 60

DATA_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")

#: Os quatro subsistemas do SIN, como o próprio ONS os identifica. Fechado de
#: propósito: sigla nova levanta em vez de virar linha ignorada em silêncio —
#: se o ONS criar um quinto subsistema, alguém tem de olhar antes de liquidar.
SUBSISTEMAS = {
    "N": "Norte",
    "NE": "Nordeste",
    "S": "Sul",
    "SE": "Sudeste/Centro-Oeste",
}

COLUNAS = ("id_subsistema", "nom_subsistema", "din_instante", "val_cargaenergiamwmed")


class FonteOnsError(FonteError):
    """Resposta inesperada do ONS. Sempre levanta — nunca degrada em valor."""


def _dia_valido(dia: str) -> str:
    if not isinstance(dia, str) or not DATA_RE.match(dia):
        raise FonteOnsError(f"dia em formato inesperado (esperado aaaa-mm-dd): {dia!r}")
    return dia


def _subsistema_valido(subsistema: str) -> str:
    if subsistema not in SUBSISTEMAS:
        raise FonteOnsError(
            f"subsistema {subsistema!r} não é do SIN — conhecidos: {sorted(SUBSISTEMAS)}"
        )
    return subsistema


def _numero(bruto: object, contexto: str) -> float:
    """MWmed como o ONS escreve: ponto decimal, sem separador de milhar.

    Ao contrário do TSE, aqui NÃO se trata ponto como separador de milhar — o
    arquivo real traz ``46535.75866666667``. Tratar o ponto como milhar
    transformaria 46 mil em 4,6 quatrilhões, calado.
    """
    texto = str(bruto).strip()
    try:
        valor = float(texto)
    except ValueError as exc:
        raise FonteOnsError(f"{contexto}: valor não numérico no ONS: {bruto!r}") from exc
    if valor != valor or valor in (float("inf"), float("-inf")):
        raise FonteOnsError(f"{contexto}: valor NaN/Infinito no ONS: {bruto!r}")
    if valor <= 0:
        raise FonteOnsError(f"{contexto}: carga não-positiva ({valor}) — o SIN não desliga")
    return valor


def _baixar_ano(ano: int, transport: Transport | None) -> list[dict]:
    url = URL_CARGA_DIARIA.format(ano=ano)
    try:
        resposta = get_bytes(
            url,
            headers={"Accept": "text/csv"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteOnsError(f"fonte oficial inalcançável: {exc}") from exc
    if resposta.status != 200:
        raise FonteOnsError(f"ONS respondeu HTTP {resposta.status} em {url}")

    try:
        texto = resposta.body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FonteOnsError(f"CSV do ONS não decodifica em UTF-8 ({exc})") from exc

    linhas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
    if not linhas:
        raise FonteOnsError(f"CSV do ONS veio vazio em {url}")
    faltando = [c for c in COLUNAS if c not in linhas[0]]
    if faltando:
        raise FonteOnsError(
            f"CSV do ONS sem as colunas {faltando} — o layout mudou: {sorted(linhas[0])}"
        )
    return linhas


def carga_do_dia(
    dia: str,
    subsistema: str,
    *,
    transport: Transport | None = None,
) -> float | None:
    """Carga de energia verificada (MWmed) do ``subsistema`` em ``dia``.

    Devolve ``None`` quando o ONS ainda não publicou aquele dia — a carga
    verificada entra no arquivo com alguns dias de atraso, e dia futuro
    simplesmente não está lá. Isso é UNKNOWN, nunca zero.
    """
    dia = _dia_valido(dia)
    subsistema = _subsistema_valido(subsistema)
    linhas = _baixar_ano(int(dia[:4]), transport)

    achadas = [
        linha
        for linha in linhas
        if str(linha["din_instante"]).strip() == dia
        and str(linha["id_subsistema"]).strip() == subsistema
    ]
    if not achadas:
        return None  # ainda não publicado — UNKNOWN over guess
    if len(achadas) > 1:
        raise FonteOnsError(
            f"o par ({dia}, {subsistema}) aparece {len(achadas)} vezes no CSV do ONS"
        )
    return _numero(achadas[0]["val_cargaenergiamwmed"], f"carga {subsistema} em {dia}")


def ultimo_dia_publicado(ano: int, *, transport: Transport | None = None) -> str:
    """O dia mais recente que o ONS já publicou naquele ano.

    Serve para a rodada saber até onde pode liquidar sem chutar, e para medir
    a defasagem real em vez de assumir a que a documentação promete.
    """
    linhas = _baixar_ano(ano, transport)
    dias = {str(linha["din_instante"]).strip() for linha in linhas}
    validos = {d for d in dias if DATA_RE.match(d)}
    if not validos:
        raise FonteOnsError(f"nenhuma data válida no CSV do ONS de {ano}")
    return max(validos)


def mediana_do_subsistema(
    ano: int,
    subsistema: str,
    *,
    transport: Transport | None = None,
) -> float:
    """Mediana da carga do subsistema no ano — o limiar do contrato.

    REGRA DA CASA: limiar sai da mediana lida da PRÓPRIA fonte, nunca escolhido
    a dedo. Um limiar escolhido por quem emite o contrato é um limiar escolhido
    para ganhar; um limiar que é a mediana da própria série deixa o contrato
    perto de 50/50 por construção, e é verificável por qualquer um que baixe o
    mesmo CSV.
    """
    subsistema = _subsistema_valido(subsistema)
    linhas = _baixar_ano(ano, transport)
    valores = [
        _numero(linha["val_cargaenergiamwmed"], f"carga {subsistema} em {linha['din_instante']}")
        for linha in linhas
        if str(linha["id_subsistema"]).strip() == subsistema
    ]
    if not valores:
        raise FonteOnsError(f"nenhuma carga de {subsistema} no CSV do ONS de {ano}")
    return statistics.median(valores)
