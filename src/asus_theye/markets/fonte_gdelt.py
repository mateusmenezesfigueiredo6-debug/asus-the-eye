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


class FonteGDELTError(RuntimeError):
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
        """Abaixo do mínimo declarado, isto é ruído amostral e não sinal."""
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

    try:
        with zipfile.ZipFile(io.BytesIO(resposta.body)) as pacote:
            nomes = pacote.namelist()
            if not nomes:
                raise FonteGDELTError(f"pacote vazio em {url}")
            bruto = pacote.read(nomes[0]).decode("utf-8", "replace")
    except (zipfile.BadZipFile, OSError) as exc:
        raise FonteGDELTError(f"pacote do GDELT ilegível ({exc})") from exc

    alvo = pais_fips.strip().upper()
    tons: list[float] = []
    for linha in bruto.splitlines():
        colunas = linha.split("\t")
        if len(colunas) <= COL_PAIS or colunas[COL_PAIS].strip().upper() != alvo:
            continue
        try:
            tons.append(float(colunas[COL_TOM]))
        except (ValueError, IndexError):
            continue  # registro sem tom não invalida os demais

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
