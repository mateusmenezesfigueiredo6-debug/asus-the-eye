# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fonte de cobertura noticiosa — GDELT, o sinal que NÃO vem do consenso.

Este conector existe por um motivo específico e vale dizê-lo: até aqui a
probabilidade da plataforma **derivava do boletim Focus**. Isso tornava
impossível afirmar desempenho próprio — seríamos o consenso com pesos
diferentes, e qualquer auditor apontaria isso.

O GDELT mede **contagem e tom da cobertura noticiosa**. Não é pesquisa com
economistas: é contagem sobre texto de notícia. Origem diferente — é esse o
ponto inteiro. E se move dias antes do boletim semanal.

**As fronteiras são impostas aqui, não pedidas pela licença.** Os termos do
GDELT permitem muito mais do que fazemos: uso irrestrito, inclusive comercial,
com direito de redistribuir e espelhar. Mesmo assim este módulo lê **duas
colunas de sessenta e uma** — contagem e tom — e nunca toca em texto de artigo,
manchete ou URL de origem. O motivo: o conteúdo apontado pertence a veículos de
imprensa, cujos termos são outros e não foram lidos. Guardar contagem não toca a
obra de ninguém; guardar manchete, sim.

Também fora, por decisão registrada em ``reports/provenance/GDELT-cobertura-noticiosa.md``:
BigQuery (é pago), a API de consulta (bloqueia mesmo com espera), e o arquivo
GKG (540 MB/dia — o de eventos, com 73 KB, basta).

**O MD5 vem publicado junto** com cada arquivo, e é conferido. Arquivo com
resumo divergente **levanta** — dado corrompido não entra na corrente, porque o
que entra selado só sai por expurgo.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

URL_ULTIMA = "https://data.gdeltproject.org/gdeltv2/lastupdate.txt"
TIMEOUT = 90
# o arquivo de eventos de 15 min tem ~73 KB comprimido; a folga cobre picos
MAX_BYTES = 8_000_000

LICENCA = "GDELT Terms of Use — uso irrestrito, inclusive comercial, sem taxa"
ATRIBUICAO = "The GDELT Project (gdeltproject.org)"

# As DUAS colunas que usamos, de 61. Declaradas por índice porque o formato não
# tem cabeçalho — e nomeadas aqui para que a fronteira fique legível.
COL_TOM = 34  # AvgTone: -100 a +100, tom médio dos documentos do evento
COL_PAIS = 53  # ActionGeo_CountryCode, FIPS 10-4 (Brasil = "BR")

# Abaixo disto a agregação não é sinal, é ruído amostral. Declarado, não mágico.
MINIMO_DE_EVENTOS = 5


class FonteGDELTError(FonteError):
    """Resposta inesperada da fonte. Sempre levanta — cobertura não se inventa."""


@dataclass(frozen=True)
class CoberturaNoticiosa:
    """Agregação de cobertura sobre um país, com a proveniência exigida."""

    pais_fips: str
    eventos: int
    tom_medio: float
    arquivo: str
    md5_do_arquivo: str
    observado_em: str
    licenca: str
    atribuicao: str

    @property
    def suficiente(self) -> bool:
        """Abaixo do mínimo declarado, isto é ruído amostral e não sinal.

        Atenção (diagnóstico 2026-09-02): ``MINIMO_DE_EVENTOS`` foi calibrado
        para o volume do DIA. Numa janela isolada de 15 minutos isto é quase
        sempre ``False`` — e está certo ser: uma fatia de 15 min de um único
        país é amostra, não cobertura. Para decidir contra o piso, use
        ``cobertura_do_dia``, que agrega as 96 janelas antes de comparar.
        """
        return self.eventos >= MINIMO_DE_EVENTOS

    def as_dict(self) -> dict[str, Any]:
        return {
            "pais_fips": self.pais_fips,
            "eventos": self.eventos,
            "tom_medio": self.tom_medio,
            "arquivo": self.arquivo,
            "md5_do_arquivo": self.md5_do_arquivo,
            "observado_em": self.observado_em,
            "suficiente": self.suficiente,
            "minimo_de_eventos": MINIMO_DE_EVENTOS,
            "licenca": self.licenca,
            "atribuicao": self.atribuicao,
            "metodo": (
                "contagem e média de AvgTone (col 34) dos eventos cujo ActionGeo_CountryCode "
                "(col 53) é o país pedido, no arquivo de eventos de 15 minutos. Duas colunas de "
                "61: texto de artigo, manchete e URL de origem NÃO são lidos — pertencem a "
                "veículos de imprensa, cujos termos são outros."
            ),
        }


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tons_do_pacote(corpo: bytes, url: str, alvo: str) -> list[float]:
    """AvgTone de cada evento do pacote cujo ActionGeo_CountryCode é *alvo*.

    Levanta ``FonteGDELTError`` para pacote vazio ou ilegível. Registro sem tom
    parseável não invalida os demais — mesma regra de sempre.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(corpo)) as pacote:
            nomes = pacote.namelist()
            if not nomes:
                raise FonteGDELTError(f"pacote vazio em {url}")
            bruto = pacote.read(nomes[0]).decode("utf-8", "replace")
    except (zipfile.BadZipFile, OSError) as exc:
        raise FonteGDELTError(f"pacote do GDELT ilegível ({exc})") from exc

    tons: list[float] = []
    for linha in bruto.splitlines():
        colunas = linha.split("\t")
        if len(colunas) <= COL_PAIS or colunas[COL_PAIS].strip().upper() != alvo:
            continue
        try:
            tons.append(float(colunas[COL_TOM]))
        except (ValueError, IndexError):
            continue  # registro sem tom não invalida os demais
    return tons


def _ultimo_arquivo(transport: Transport | None) -> tuple[str, str]:
    """URL e MD5 do arquivo de eventos mais recente, do índice publicado.

    O índice traz três linhas — eventos, menções e GKG — no formato
    ``tamanho md5 url``. Usamos só a de eventos.
    """
    try:
        resposta = get_bytes(
            URL_ULTIMA, headers={"Accept": "text/plain"}, timeout=TIMEOUT, max_bytes=100_000, transport=transport
        )
    except HttpError as exc:
        raise FonteGDELTError(f"índice do GDELT inalcançável: {exc}") from exc
    if resposta.status != 200:
        raise FonteGDELTError(f"índice do GDELT respondeu HTTP {resposta.status}")

    for linha in resposta.body.decode("utf-8", "replace").splitlines():
        partes = linha.split()
        if len(partes) == 3 and partes[2].endswith(".export.CSV.zip"):
            # o índice publica http; forçamos https — o redirecionamento entre
            # esquemas não é seguido pelo transporte, por desenho
            return partes[2].replace("http://", "https://", 1), partes[1]
    raise FonteGDELTError("índice do GDELT não trouxe arquivo de eventos — formato inesperado")


def cobertura(
    pais_fips: str = "BR",
    *,
    transport: Transport | None = None,
) -> CoberturaNoticiosa:
    """Contagem e tom médio da cobertura sobre *pais_fips* na janela mais recente.

    Levanta se a fonte estiver inalcançável, se o MD5 divergir, ou se o arquivo
    vier malformado. Ausência de cobertura **não** levanta: devolve contagem
    zero com ``suficiente=False``, e quem chama decide — que é a diferença entre
    "não sei" e "deu erro".

    Isto mede UMA janela de 15 minutos — amostra pontual, não o dia. Para a
    cobertura do dia (o regime do piso ``MINIMO_DE_EVENTOS``), use
    ``cobertura_do_dia``.
    """
    if not pais_fips.strip():
        raise FonteGDELTError("pais_fips obrigatório (FIPS 10-4, ex.: 'BR')")

    url, md5_esperado = _ultimo_arquivo(transport)
    try:
        resposta = get_bytes(
            url, headers={"Accept": "application/zip"}, timeout=TIMEOUT, max_bytes=MAX_BYTES, transport=transport
        )
    except HttpError as exc:
        raise FonteGDELTError(f"arquivo do GDELT inalcançável: {exc}") from exc
    if resposta.status != 200:
        raise FonteGDELTError(f"arquivo do GDELT respondeu HTTP {resposta.status} em {url}")

    md5_obtido = hashlib.md5(resposta.body, usedforsecurity=False).hexdigest()
    if md5_obtido != md5_esperado:
        raise FonteGDELTError(
            f"MD5 divergente para {url}: esperado {md5_esperado}, obtido {md5_obtido}. "
            "Arquivo corrompido não vira dado — o que entra selado só sai por expurgo."
        )

    alvo = pais_fips.strip().upper()
    tons = _tons_do_pacote(resposta.body, url, alvo)

    return CoberturaNoticiosa(
        pais_fips=alvo,
        eventos=len(tons),
        tom_medio=round(sum(tons) / len(tons), 4) if tons else 0.0,
        arquivo=url.rsplit("/", 1)[-1],
        md5_do_arquivo=md5_esperado,
        observado_em=_agora(),
        licenca=LICENCA,
        atribuicao=ATRIBUICAO,
    )


# ----------------------------------------------------------- o dia inteiro
#
# O conserto do diagnóstico de 2026-09-02: o defeito não era coluna nem
# arquivo — era medir UMA janela de 15 minutos contra um piso calibrado para
# o DIA. Aqui as 96 janelas do dia UTC são somadas ANTES do piso.

# 24 horas × 4 janelas de 15 minutos. Declarado, não mágico.
JANELAS_POR_DIA = 96

# As janelas moram no mesmo diretório do índice, com URL previsível
# ``{AAAAMMDDHHMMSS}.export.CSV.zip`` — o mesmo padrão que ``lastupdate.txt``
# publica para a janela mais recente. Derivado do índice, não inventado.
_BASE_JANELAS = URL_ULTIMA.rsplit("/", 1)[0]


@dataclass(frozen=True)
class CoberturaDia:
    """Agregado da cobertura de um país no dia UTC inteiro — o regime do piso.

    ``janelas_ok``/``janelas_falhas`` declaram com quantas das 96 janelas o
    agregado foi feito: janela ausente não vira zero silencioso, vira número.
    """

    dia: str
    pais_fips: str
    eventos: int
    tom_medio: float
    janelas_ok: int
    janelas_falhas: int
    metodo: str
    observado_em: str
    licenca: str
    atribuicao: str

    @property
    def suficiente(self) -> bool:
        """A MESMA constante de sempre — agora comparada ao agregado do dia,
        que é o regime para o qual ela foi calibrada."""
        return self.eventos >= MINIMO_DE_EVENTOS

    def as_dict(self) -> dict[str, Any]:
        return {
            "dia": self.dia,
            "pais_fips": self.pais_fips,
            "eventos": self.eventos,
            "tom_medio": self.tom_medio,
            "janelas_ok": self.janelas_ok,
            "janelas_falhas": self.janelas_falhas,
            "observado_em": self.observado_em,
            "suficiente": self.suficiente,
            "minimo_de_eventos": MINIMO_DE_EVENTOS,
            "licenca": self.licenca,
            "atribuicao": self.atribuicao,
            "metodo": self.metodo,
        }


def _carimbos_do_dia(dia: str) -> list[str]:
    """Os 96 carimbos ``AAAAMMDDHHMMSS`` do dia UTC, de 00:00:00 a 23:45:00.

    Levanta ANTES de qualquer rede se o dia vier malformado — data torta não
    vira 96 URLs tortas.
    """
    try:
        interpretado = datetime.strptime(dia, "%Y-%m-%d")
    except ValueError as exc:
        raise FonteGDELTError(f"dia malformado: {dia!r} — use AAAA-MM-DD (dia UTC, ex.: '2026-08-21')") from exc
    # strptime aceita '2026-8-2'; o formato do arquivo, não. Ida e volta fecha a porta.
    if interpretado.strftime("%Y-%m-%d") != dia:
        raise FonteGDELTError(f"dia malformado: {dia!r} — use AAAA-MM-DD (dia UTC, ex.: '2026-08-21')")
    compacto = interpretado.strftime("%Y%m%d")
    return [f"{compacto}{hora:02d}{minuto:02d}00" for hora in range(24) for minuto in (0, 15, 30, 45)]


def cobertura_do_dia(
    dia: str,
    *,
    pais_fips: str = "BR",
    transport: Transport | None = None,
) -> CoberturaDia:
    """Contagem e tom médio da cobertura sobre *pais_fips* no dia UTC inteiro.

    Baixa as 96 janelas de 15 minutos do dia (URL previsível, mesmo diretório
    do índice), SOMA os eventos e pondera o tom por eventos — só então o piso
    ``MINIMO_DE_EVENTOS`` faz sentido, porque foi calibrado para este regime.

    Janela indisponível (404, transporte caído, pacote ilegível) **não**
    derruba o dia: conta em ``janelas_falhas`` e o ``metodo`` declara com
    quantas janelas o agregado foi feito. Se TODAS falharem, levanta — dia
    inteiro sem fonte é erro de fonte, não cobertura zero. Já ausência de
    eventos nas janelas que responderam **não** levanta: devolve contagem zero
    com ``suficiente=False``, e quem chama decide — a diferença entre "não
    sei" e "deu erro".

    Sem MD5 por janela, e de propósito: ``lastupdate.txt`` só publica o resumo
    da janela mais recente, e conferir 96 janelas exigiria o ``masterfilelist``
    (dezenas de MB por consulta) — fora do orçamento declarado no cabeçalho.
    Pacote corrompido ainda é detectado pela própria descompactação, e vira
    janela falha, não dado.
    """
    if not pais_fips.strip():
        raise FonteGDELTError("pais_fips obrigatório (FIPS 10-4, ex.: 'BR')")
    carimbos = _carimbos_do_dia(dia)  # levanta antes da rede se o dia for torto

    alvo = pais_fips.strip().upper()
    eventos = 0
    soma_de_tons = 0.0
    janelas_ok = 0
    janelas_falhas = 0
    for carimbo in carimbos:
        url = f"{_BASE_JANELAS}/{carimbo}.export.CSV.zip"
        try:
            resposta = get_bytes(
                url, headers={"Accept": "application/zip"}, timeout=TIMEOUT, max_bytes=MAX_BYTES, transport=transport
            )
            if resposta.status != 200:
                raise FonteGDELTError(f"janela respondeu HTTP {resposta.status} em {url}")
            tons = _tons_do_pacote(resposta.body, url, alvo)
        except (HttpError, FonteGDELTError):
            # O GDELT pula janelas de vez em quando; uma ausente não derruba o
            # dia — ela vira número em janelas_falhas, visível no registro.
            janelas_falhas += 1
            continue
        janelas_ok += 1
        eventos += len(tons)
        soma_de_tons += sum(tons)

    if janelas_ok == 0:
        raise FonteGDELTError(
            f"todas as {len(carimbos)} janelas de {dia} falharam — dia inteiro sem fonte é erro, não cobertura zero"
        )

    return CoberturaDia(
        dia=dia,
        pais_fips=alvo,
        eventos=eventos,
        # ponderação por eventos: somar TODOS os tons e dividir pelo total
        # equivale à média das janelas pesada pela contagem de cada uma.
        tom_medio=round(soma_de_tons / eventos, 4) if eventos else 0.0,
        janelas_ok=janelas_ok,
        janelas_falhas=janelas_falhas,
        metodo=(
            f"agregado de {janelas_ok} janelas de 15min do dia UTC {dia} "
            f"({janelas_falhas} ausentes de {len(carimbos)}): soma dos eventos cujo "
            "ActionGeo_CountryCode (col 53) é o país pedido e média de AvgTone (col 34) "
            "ponderada por eventos. Duas colunas de 61: texto de artigo, manchete e URL "
            "de origem NÃO são lidos — pertencem a veículos de imprensa, cujos termos são outros."
        ),
        observado_em=_agora(),
        licenca=LICENCA,
        atribuicao=ATRIBUICAO,
    )
