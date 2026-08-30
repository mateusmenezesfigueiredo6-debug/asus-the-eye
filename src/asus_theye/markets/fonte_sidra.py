# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: IBGE/SIDRA, tabela 7060 — IPCA por grupo e subitem.

Este conector existe para os mercados do dia a dia: a comida, a conta de luz,
o gás de botijão, a gasolina, o arroz. O IPCA cheio não fala essa língua — a
inflação "oficial" pode vir em 0,07% no mesmo mês em que a energia elétrica
subiu 3,09% e o feijão preto 3,28%. Quem sente o aperto sente o subitem.

POR QUE O SIDRA E NÃO O SGS. O Banco Central espelha os grupos do IPCA em
séries SGS (1635 em diante) e seria mais barato usá-las: o fetcher do BCB já é
parametrizável por série. O problema é que **o SGS não publica metadados por
API** — nenhum endpoint devolve o nome da série. A identidade "1635 é
Alimentação e bebidas" ficaria sendo uma suposição nossa para sempre, e o dia
em que o BCB reorganizasse a família, o mercado liquidaria contra o índice
errado sem nada acusar.

O SIDRA devolve o **nome junto com o valor**. Isso permite a guarda que dá nome
a este módulo: a cada leitura conferimos que o código ainda corresponde ao item
que o mercado diz medir. Fonte que muda de significado passa a ser um erro
barulhento, não uma liquidação silenciosamente errada.

A API é pública e sem chave. O transporte é injetável (``net.http.Transport``)
para a suíte rodar offline.
"""

from __future__ import annotations

import json
import unicodedata

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

TABELA_IPCA = 7060
VARIAVEL_VARIACAO_MENSAL = 63
URL_VALORES = (
    "https://apisidra.ibge.gov.br/values"
    "/t/{tabela}/n1/all/v/{variavel}/p/{periodo}/c315/{codigo}"
)
MAX_BYTES = 200_000
TIMEOUT = 30


class FonteSidraError(FonteError):
    """Resposta inesperada do IBGE. Sempre levanta — nunca degrada em valor."""


def _periodo_sidra(mes_referencia: str) -> str:
    """Converte ``aaaa-mm`` no ``aaaamm`` que o SIDRA espera."""
    try:
        ano_txt, mes_txt = mes_referencia.split("-")
        ano, mes = int(ano_txt), int(mes_txt)
        if not 1 <= mes <= 12:
            raise ValueError(mes)
    except ValueError as exc:
        raise FonteSidraError(f"mês de referência em formato inesperado: {mes_referencia!r}") from exc
    return f"{ano:04d}{mes:02d}"


def _sem_acento(texto: str) -> str:
    """Compara nomes sem tropeçar em acento ou caixa — nunca ignorando palavra."""
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c)).casefold().strip()


def variacao_mensal(
    mes_referencia: str,
    *,
    codigo: int,
    nome_esperado: str,
    transport: Transport | None = None,
) -> float | None:
    """Variação mensal do IPCA (%) para um grupo/subitem, em ``mes_referencia``.

    ``codigo`` é o código da classificação ``c315`` do SIDRA (ex.: 7170 para
    "1.Alimentação e bebidas", 7484 para "2202.Energia elétrica residencial").
    ``nome_esperado`` é o rótulo que o mercado afirma medir: se o IBGE devolver
    outro item para aquele código, isto levanta em vez de liquidar errado.

    Devolve ``None`` se o mês ainda não foi publicado — o SIDRA responde apenas
    com o cabeçalho nesse caso, e isso é UNKNOWN, nunca zero.
    """
    url = URL_VALORES.format(
        tabela=TABELA_IPCA,
        variavel=VARIAVEL_VARIACAO_MENSAL,
        periodo=_periodo_sidra(mes_referencia),
        codigo=int(codigo),
    )
    try:
        response = get_bytes(
            url,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteSidraError(f"fonte oficial inalcançável: {exc}") from exc
    if response.status != 200:
        raise FonteSidraError(f"fonte oficial respondeu HTTP {response.status} em {url}")

    try:
        linhas = json.loads(response.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FonteSidraError(f"resposta do IBGE não é JSON válido ({exc})") from exc
    if not isinstance(linhas, list) or not linhas:
        raise FonteSidraError(f"resposta do IBGE em formato inesperado: {type(linhas).__name__}")

    # linhas[0] é sempre o dicionário de rótulos das colunas; os dados vêm depois.
    dados = [linha for linha in linhas[1:] if isinstance(linha, dict)]
    if not dados:
        return None  # mês ainda não publicado — UNKNOWN over guess
    if len(dados) > 1:
        raise FonteSidraError(f"esperava 1 observação para {codigo} em {mes_referencia}, vieram {len(dados)}")

    linha = dados[0]
    for campo in ("V", "D3C", "D4C", "D4N", "MN"):
        if campo not in linha:
            raise FonteSidraError(f"observação do IBGE sem o campo {campo!r}: {linha!r}")

    # A guarda que justifica este conector: código e nome têm de continuar
    # casando, senão o mercado estaria medindo outra coisa sem avisar ninguém.
    if str(linha["D4C"]) != str(int(codigo)):
        raise FonteSidraError(f"IBGE devolveu o código {linha['D4C']!r}, não o {codigo!r} pedido")
    if _sem_acento(nome_esperado) not in _sem_acento(str(linha["D4N"])):
        raise FonteSidraError(
            f"código {codigo} mudou de significado: o mercado mede {nome_esperado!r}, "
            f"o IBGE devolveu {linha['D4N']!r} — não liquida até alguém conferir"
        )
    if str(linha["D3C"]) != _periodo_sidra(mes_referencia):
        raise FonteSidraError(f"observação fora do mês pedido: {linha['D3C']!r} != {mes_referencia}")
    if str(linha["MN"]).strip() != "%":
        raise FonteSidraError(f"unidade mudou na fonte: esperava '%', veio {linha['MN']!r}")

    bruto = str(linha["V"]).strip()
    # O SIDRA usa "..." e "-" para dado ausente na célula; não é zero.
    if bruto in {"...", "-", "..", "X", ""}:
        return None
    try:
        return float(bruto.replace(",", "."))
    except ValueError as exc:
        raise FonteSidraError(f"valor não numérico do IBGE: {bruto!r}") from exc
