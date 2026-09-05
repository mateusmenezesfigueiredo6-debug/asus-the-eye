# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: ANP — preço de combustível na bomba, por UF.

POR QUE ESTA FONTE. É o preço que a pessoa vê todo dia no caminho do trabalho —
mais concreto que qualquer índice. E, tecnicamente, é a fonte oficial brasileira
gratuita com a MELHOR granularidade geográfica que achamos: coleta por posto,
com Unidade da Federação e município. O maior erro medido do modelo eleitoral é
justamente geográfico (2,38 pp na média, **26,37 pp no pior estado**), e séries
nacionais não ajudam nisso. Vinte e sete UFs × três produtos = 81 desfechos por
mês, cada um num recorte diferente do país.

TUDO ABAIXO FOI CONFERIDO AO VIVO EM 31/08/2026, não deduzido de documentação.

  Índice oficial (é dele que saem os nomes de arquivo):
    /anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis
    -> 200. Lista 18 arquivos de 2026.

  Um arquivo real:
    .../arquivos/shpc/dsan/2026/07-dados-abertos-precos-gasolina-etanol.csv
    -> 200, 8.449.075 bytes, 49.424 linhas, coletas de 01/07 a 31/07/2026
    produtos: GASOLINA 18.876 · GASOLINA ADITIVADA 14.448 · ETANOL 16.100
    medianas de GASOLINA: RR 7,57 · RO 7,39 · AM 7,29 · BA 6,99 · CE 6,97 …

O NOME DO ARQUIVO NÃO SE ADIVINHA. A ANP não segue um padrão estável: convivem
``07-dados-abertos-precos-gasolina-etanol.csv`` e, no mesmo índice,
``02-cados-abertos-preco-gasolina-etanol.csv`` — com "cados" e "preco" no
singular. Um conector que montasse o nome por template acertaria em uns meses e
daria 404 silencioso em outros. Por isso aqui se LÊ O ÍNDICE e se casa por
padrão, sempre.

DEFASAGEM DE UM MÊS, MEDIDA. Em 31/08/2026 o arquivo de agosto ainda devolvia
404; o mais recente era julho. Logo o contrato é MENSAL e liquida no mês
seguinte. Está escrito no critério do mercado, não escondido.

LGPD — O QUE ESTE MÓDULO SE RECUSA A DEVOLVER. O CSV traz, por posto:
``Revenda`` (razão social), ``CNPJ da Revenda``, ``Nome da Rua``, ``Numero Rua``
e ``Cep``. Nada disso é necessário para liquidar um contrato sobre preço
mediano, e o que não é necessário não se coleta — minimização, art. 6º III da
LGPD. As funções públicas daqui devolvem **somente agregado** (mediana, contagem
e as siglas), e as colunas identificadoras são descartadas na leitura. Não é
zelo decorativo: um banco com CNPJ e endereço de milhares de postos seria um
passivo que o produto não precisa carregar para funcionar.

O transporte é injetável (``net.http.Transport``) para a suíte rodar offline.
"""

from __future__ import annotations

import csv
import io
import re
import statistics
import unicodedata
from dataclasses import dataclass

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

BASE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos"
URL_INDICE = f"{BASE}/serie-historica-de-precos-de-combustiveis"
MAX_BYTES = 60_000_000
TIMEOUT = 180

#: Produtos que este conector aceita. Fechado: rótulo novo levanta em vez de
#: virar série vazia — série vazia liquidaria como "não publicado" para sempre.
PRODUTOS = frozenset({"GASOLINA", "GASOLINA ADITIVADA", "ETANOL", "DIESEL", "DIESEL S10", "GLP", "GNV"})

#: As 27 unidades da federação. Fechado pelo mesmo motivo.
UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)

#: Colunas que este módulo se recusa a propagar — ver a nota de LGPD acima.
COLUNAS_IDENTIFICADORAS = frozenset(
    {"Revenda", "CNPJ da Revenda", "Nome da Rua", "Numero Rua", "Complemento", "Bairro", "Cep"}
)

COLUNAS_NECESSARIAS = ("Estado - Sigla", "Municipio", "Produto", "Data da Coleta", "Valor de Venda")


class FonteAnpError(FonteError):
    """Resposta inesperada da ANP. Sempre levanta — nunca degrada em valor."""


class MesNaoPublicado(FonteAnpError):
    """A ANP ainda não publicou aquele mês.

    Subclasse própria porque este caso é NORMAL até o mês seguinte fechar, e
    quem chama precisa distinguir "ainda não saiu" de "a fonte quebrou".
    Confundir os dois transformaria a espera mensal em alarme, todo mês.
    """


@dataclass(frozen=True)
class PrecoMediano:
    """Agregado por UF — e SÓ o agregado. Ver a nota de LGPD no módulo."""

    uf: str
    produto: str
    competencia: str  # aaaa-mm
    mediana: float
    coletas: int


def _competencia_valida(competencia: str) -> tuple[int, int]:
    if not isinstance(competencia, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", competencia):
        raise FonteAnpError(f"competência em formato inesperado (esperado aaaa-mm): {competencia!r}")
    ano, mes = competencia.split("-")
    return int(ano), int(mes)


def _produto_valido(produto: str) -> str:
    alvo = str(produto).strip().upper()
    if alvo not in PRODUTOS:
        raise FonteAnpError(f"produto {alvo!r} fora do escopo — conhecidos: {sorted(PRODUTOS)}")
    return alvo


def _uf_valida(uf: str) -> str:
    alvo = str(uf).strip().upper()
    if alvo not in UFS:
        raise FonteAnpError(f"UF {alvo!r} não é unidade da federação")
    return alvo


def _preco(bruto: object, contexto: str) -> float:
    """Preço como a ANP escreve: vírgula decimal (``'6,69'``)."""
    texto = str(bruto).strip().replace(",", ".")
    try:
        valor = float(texto)
    except ValueError as exc:
        raise FonteAnpError(f"{contexto}: preço não numérico na ANP: {bruto!r}") from exc
    if valor != valor or valor in (float("inf"), float("-inf")):
        raise FonteAnpError(f"{contexto}: preço NaN/Infinito na ANP: {bruto!r}")
    if valor <= 0:
        raise FonteAnpError(f"{contexto}: preço não-positivo ({valor}) — combustível não é de graça")
    return valor


def _buscar(url: str, transport: Transport | None, aceita: str) -> bytes:
    try:
        resposta = get_bytes(
            url,
            headers={"Accept": aceita},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteAnpError(f"fonte oficial inalcançável: {exc}") from exc
    if resposta.status == 404:
        raise MesNaoPublicado(f"a ANP ainda não publicou {url}")
    if resposta.status != 200:
        raise FonteAnpError(f"ANP respondeu HTTP {resposta.status} em {url}")
    return resposta.body


def arquivos_do_ano(ano: int, *, transport: Transport | None = None) -> list[str]:
    """Caminhos de CSV que o índice oficial da ANP lista para aquele ano.

    Lê o índice em vez de montar o nome por template — ver a nota do módulo
    sobre ``cados-abertos``: a ANP não mantém padrão de nome, e adivinhar dá
    404 silencioso em alguns meses.
    """
    corpo = _buscar(URL_INDICE, transport, "text/html")
    try:
        html = corpo.decode("utf-8", errors="replace")
    except UnicodeDecodeError as exc:  # pragma: no cover - decode com replace não levanta
        raise FonteAnpError(f"índice da ANP não decodifica ({exc})") from exc
    achados = sorted(set(re.findall(rf"shpc/dsan/{ano}/[^\"'\s>]+\.csv", html)))
    if not achados:
        raise MesNaoPublicado(f"o índice da ANP não lista nenhum CSV de {ano}")
    return achados


def _csv_do_mes(ano: int, mes: int, produto: str, transport: Transport | None) -> str:
    """Acha, no índice, o CSV que cobre aquele mês e aquele produto."""
    # A ANP agrupa produtos por arquivo: gasolina+etanol num, diesel+gnv noutro,
    # glp num terceiro. O casamento é por palavra-chave, não por nome exato.
    familia = (
        "glp"
        if produto == "GLP"
        else "diesel" if produto in {"DIESEL", "DIESEL S10", "GNV"} else "gasolina"
    )
    prefixo = f"{mes:02d}-"
    candidatos = [
        c
        for c in arquivos_do_ano(ano, transport=transport)
        if c.rsplit("/", 1)[-1].startswith(prefixo) and familia in c.rsplit("/", 1)[-1].lower()
    ]
    if not candidatos:
        raise MesNaoPublicado(
            f"a ANP ainda não publicou {ano}-{mes:02d} para a família {familia!r}"
        )
    if len(candidatos) > 1:
        raise FonteAnpError(
            f"o índice da ANP lista {len(candidatos)} arquivos para {ano}-{mes:02d}/{familia}: "
            f"{candidatos} — ambíguo, não liquida até alguém conferir"
        )
    return candidatos[0]


def preco_mediano(
    competencia: str,
    uf: str,
    produto: str,
    *,
    transport: Transport | None = None,
) -> PrecoMediano | None:
    """Mediana do preço de venda do ``produto`` na ``uf``, na ``competencia``.

    Devolve ``None`` quando o mês existe mas não há coleta daquele par
    (UF, produto) — a ANP não cobre todo produto em todo estado. Isso é UNKNOWN,
    nunca zero.

    Levanta ``MesNaoPublicado`` quando o mês inteiro ainda não saiu, que é o
    estado normal até o mês seguinte fechar.

    NÃO devolve CNPJ, razão social nem endereço — ver a nota de LGPD do módulo.
    """
    ano, mes = _competencia_valida(competencia)
    produto = _produto_valido(produto)
    uf = _uf_valida(uf)

    # O índice devolve o caminho relativo (``shpc/dsan/2026/07-....csv``); a URL
    # completa é sempre ``{BASE}/arquivos/{caminho}``. Conferido ao vivo.
    caminho = _csv_do_mes(ano, mes, produto, transport)
    corpo = _buscar(f"{BASE}/arquivos/{caminho}", transport, "text/csv")

    try:
        texto = corpo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = corpo.decode("latin-1")

    linhas = csv.DictReader(io.StringIO(texto), delimiter=";")
    campos = linhas.fieldnames or []
    faltando = [c for c in COLUNAS_NECESSARIAS if c not in campos]
    if faltando:
        raise FonteAnpError(
            f"CSV da ANP sem as colunas {faltando} — o layout mudou: {sorted(campos)}"
        )

    # Só o preço entra na lista. As colunas identificadoras nem são lidas —
    # minimização de dado, não filtragem depois do fato.
    valores = [
        _preco(linha["Valor de Venda"], f"{produto} em {uf}, {competencia}")
        for linha in linhas
        if str(linha["Estado - Sigla"]).strip().upper() == uf
        and str(linha["Produto"]).strip().upper() == produto
        and str(linha["Valor de Venda"]).strip()
    ]
    if not valores:
        return None  # par (UF, produto) sem coleta no mês — UNKNOWN over guess
    return PrecoMediano(
        uf=uf,
        produto=produto,
        competencia=competencia,
        mediana=statistics.median(valores),
        coletas=len(valores),
    )


@dataclass(frozen=True)
class PrecoMedianoMunicipio:
    """Agregado por MUNICÍPIO — e só o agregado, com piso de k-anonimato.

    Mesma doutrina do ``PrecoMediano``: nada de revenda, CNPJ ou endereço. A
    diferença é que o recorte municipal exige uma proteção a mais, explicada em
    ``preco_mediano_municipio``.
    """

    uf: str
    municipio: str
    produto: str
    competencia: str  # aaaa-mm
    mediana: float
    coletas: int


# PISO DE K-ANONIMATO — por que 20, e por que existe.
#
# Município NÃO é dado pessoal, mas a MEDIANA de um município com dois ou três
# postos É, na prática, o preço de um estabelecimento identificável: quem
# conhece a cidade sabe de quem é o número. Publicar isso seria fazer pela
# porta dos fundos o que o módulo se recusa a fazer pela porta da frente (ver a
# nota de LGPD no topo). É o mesmo problema que institutos de estatística
# resolvem com supressão de célula.
#
# O valor 20 é ESCOLHA DE POLÍTICA sustentada por medição feita em 04/09/2026
# sobre o CSV real de julho (GASOLINA, 414 municípios com coleta):
#     < 2 coletas:   5 municípios (1%)      < 10 coletas:  17 (4%)
#     < 5 coletas:   8 municípios (2%)      < 20 coletas:  40 (10%)
#     mediana de coletas por município: 36 · máximo: 888 (São Paulo)
# Com o piso em 20 sobram 374 municípios (90% da cobertura) e a mediana passa a
# ser o valor do décimo posto ordenado — nenhum estabelecimento isolado se lê
# ali. O piso clássico de 5 seria permissivo demais para uma MEDIANA de preço.
#
# Município abaixo do piso devolve ``None``, exatamente como par (UF, produto)
# sem coleta: UNKNOWN over guess. Não se inventa número, e não se publica o
# preço do posto do seu Zé.
PISO_K_ANONIMATO = 20


def preco_mediano_municipio(
    competencia: str,
    uf: str,
    municipio: str,
    produto: str,
    *,
    minimo_coletas: int = PISO_K_ANONIMATO,
    transport: Transport | None = None,
) -> PrecoMedianoMunicipio | None:
    """Mediana do ``produto`` naquele município, ou ``None``.

    Devolve ``None`` em dois casos, deliberadamente indistinguíveis para quem
    chama porque ambos significam "não liquida": o município não teve coleta no
    mês, ou teve MENOS que ``minimo_coletas`` — ver ``PISO_K_ANONIMATO``.

    O nome do município é comparado sem acento e sem caixa, porque a ANP grafa
    "SAO PAULO" num mês e "São Paulo" noutro — casar por igualdade crua daria
    404 silencioso de dado, que é o pior tipo.
    """
    ano, mes = _competencia_valida(competencia)
    produto = _produto_valido(produto)
    uf = _uf_valida(uf)
    alvo = _normalizar_municipio(municipio)
    if not alvo:
        raise FonteAnpError("município vazio")
    if minimo_coletas < 1:
        raise FonteAnpError(f"piso de k-anonimato inválido: {minimo_coletas}")

    caminho = _csv_do_mes(ano, mes, produto, transport)
    corpo = _buscar(f"{BASE}/arquivos/{caminho}", transport, "text/csv")
    try:
        texto = corpo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = corpo.decode("latin-1")

    linhas = csv.DictReader(io.StringIO(texto), delimiter=";")
    campos = linhas.fieldnames or []
    faltando = [c for c in COLUNAS_NECESSARIAS if c not in campos]
    if faltando:
        raise FonteAnpError(
            f"CSV da ANP sem as colunas {faltando} — o layout mudou: {sorted(campos)}"
        )

    valores = [
        _preco(linha["Valor de Venda"], f"{produto} em {municipio}/{uf}, {competencia}")
        for linha in linhas
        if str(linha["Estado - Sigla"]).strip().upper() == uf
        and _normalizar_municipio(linha["Municipio"]) == alvo
        and str(linha["Produto"]).strip().upper() == produto
        and str(linha["Valor de Venda"]).strip()
    ]
    if len(valores) < minimo_coletas:
        return None  # sem coleta OU abaixo do piso — os dois significam "não liquida"
    return PrecoMedianoMunicipio(
        uf=uf,
        municipio=alvo,
        produto=produto,
        competencia=competencia,
        mediana=statistics.median(valores),
        coletas=len(valores),
    )


def _normalizar_municipio(nome: object) -> str:
    """Caixa alta, sem acento, espaços colapsados — para casar grafias da ANP."""
    texto = unicodedata.normalize("NFD", str(nome or "").strip().upper())
    sem_acento = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.split())
