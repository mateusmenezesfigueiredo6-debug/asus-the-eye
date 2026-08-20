# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fonte GLOBAL — indicadores do Banco Mundial (CC-BY 4.0).

O que este conector destrava: mercados fora do Brasil. Até aqui toda pergunta
resolvia contra o BCB, o que limitava a plataforma a um país. O Banco Mundial
publica inflação, PIB, desemprego e câmbio de dezenas de economias sob
**CC-BY 4.0** — licença que permite copiar, modificar e distribuir **inclusive
para fim comercial**, exigindo apenas atribuição.

Por que esta fonte e não outra: a licença é o critério. Comparadores
proprietários restringem armazenar, exibir e derivar — exatamente o que uma
plataforma de prova precisa fazer. CC-BY não restringe nada disso; cobra
atribuição, e atribuição nós damos de bom grado, carimbada no próprio evento
selado.

**A atribuição viaja no dado, não num rodapé.** Cada observação carrega
``atribuicao`` e ``licenca``, de modo que a exigência da licença é cumprida em
qualquer lugar que o dado apareça — painel, export estático, API — sem depender
de alguém lembrar de escrever no rodapé.

**Anualidade declarada.** Estes indicadores são ANUAIS. Uma pergunta mensal não
pode resolver contra eles, e o conector diz isso em vez de deixar o chamador
descobrir do jeito difícil.

Doutrina de sempre: fonte oficial nomeada, UNKNOWN over guess (ano sem
publicação devolve ``None``, nunca zero), resposta malformada LEVANTA.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from asus_theye.net.http import HttpError, Transport, get_bytes

URL_BASE = "https://api.worldbank.org/v2"
TIMEOUT = 30
MAX_BYTES = 500_000

# Exigência da CC-BY 4.0, cumprida no dado e não num rodapé esquecível.
LICENCA = "CC-BY-4.0"
ATRIBUICAO = "World Bank Open Data (data.worldbank.org) — CC BY 4.0"

# Indicadores admitidos. A lista é curta de propósito: cada entrada declara a
# unidade e a periodicidade, sem as quais o número não é interpretável — 3,1 em
# "% ao ano" e 3,1 em "% do PIB" são coisas diferentes.
INDICADORES: dict[str, dict[str, str]] = {
    "FP.CPI.TOTL.ZG": {"nome": "Inflação anual (IPC)", "unidade": "percentual_anual", "periodicidade": "anual"},
    "NY.GDP.MKTP.KD.ZG": {"nome": "Crescimento do PIB", "unidade": "percentual_anual", "periodicidade": "anual"},
    "SL.UEM.TOTL.ZS": {
        "nome": "Desemprego (% da força de trabalho)",
        "unidade": "percentual_anual",
        "periodicidade": "anual",
    },
}

# ISO-3 do país. Validado porque um código errado devolve lista vazia, que é
# indistinguível de "ano não publicado" — e confundir os dois viraria UNKNOWN
# onde na verdade houve erro de chamada.
ISO3_RE = re.compile(r"^[A-Za-z]{3}$")
ANO_RE = re.compile(r"^\d{4}$")


class FonteWorldBankError(RuntimeError):
    """Resposta inesperada da fonte global. Sempre levanta — valor não se inventa."""


@dataclass(frozen=True)
class ObservacaoGlobal:
    """Um valor publicado, com país, ano, unidade e a atribuição exigida pela licença."""

    indicador: str
    nome_do_indicador: str
    pais_iso3: str
    nome_do_pais: str
    ano: str
    valor: float
    unidade: str
    periodicidade: str
    licenca: str
    atribuicao: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "indicador": self.indicador,
            "nome_do_indicador": self.nome_do_indicador,
            "pais_iso3": self.pais_iso3,
            "nome_do_pais": self.nome_do_pais,
            "ano": self.ano,
            "valor": self.valor,
            "unidade": self.unidade,
            "periodicidade": self.periodicidade,
            "licenca": self.licenca,
            "atribuicao": self.atribuicao,
        }


def indicador_anual(
    indicador: str,
    pais_iso3: str,
    ano: str,
    *,
    transport: Transport | None = None,
) -> ObservacaoGlobal | None:
    """Valor publicado do indicador para o país e ano — ou ``None`` se não publicado.

    ``None`` significa UMA coisa: o ano ainda não foi publicado para aquele país.
    Erro de chamada (indicador desconhecido, ISO-3 malformado) levanta, para não
    se disfarçar de UNKNOWN.
    """
    config = INDICADORES.get(indicador)
    if config is None:
        raise FonteWorldBankError(
            f"indicador {indicador!r} fora do registro admitido: {sorted(INDICADORES)}. "
            "Cada indicador precisa declarar unidade e periodicidade antes de entrar."
        )
    if not ISO3_RE.fullmatch(pais_iso3):
        raise FonteWorldBankError(f"pais_iso3 deve ser código ISO-3 (ex.: 'BRA'), veio {pais_iso3!r}")
    if not ANO_RE.fullmatch(ano):
        raise FonteWorldBankError(f"ano deve ter 4 dígitos, veio {ano!r}")

    url = f"{URL_BASE}/country/{pais_iso3.upper()}/indicator/{indicador}?format=json&date={ano}:{ano}"
    try:
        resposta = get_bytes(
            url, headers={"Accept": "application/json"}, timeout=TIMEOUT, max_bytes=MAX_BYTES, transport=transport
        )
    except HttpError as exc:
        raise FonteWorldBankError(f"fonte global inalcançável: {exc}") from exc
    if resposta.status != 200:
        raise FonteWorldBankError(f"fonte global respondeu HTTP {resposta.status} em {url}")

    try:
        corpo = json.loads(resposta.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FonteWorldBankError(f"resposta do Banco Mundial não é JSON válido ({exc})") from exc

    # O formato é [metadados, dados]; a API sinaliza erro devolvendo só o
    # primeiro elemento, com uma chave "message" — caso que precisa LEVANTAR e
    # não virar UNKNOWN silencioso.
    if not isinstance(corpo, list) or not corpo:
        raise FonteWorldBankError(f"resposta em formato inesperado: {type(corpo).__name__}")
    if len(corpo) == 1:
        raise FonteWorldBankError(f"a fonte recusou a consulta (país ou indicador inválido): {corpo[0]!r}")

    pontos = corpo[1]
    if pontos is None or not isinstance(pontos, list) or not pontos:
        return None  # ano não publicado para este país — UNKNOWN honesto

    ponto = pontos[0]
    if not isinstance(ponto, dict) or "value" not in ponto:
        raise FonteWorldBankError(f"ponto em formato inesperado: {ponto!r}")
    if ponto["value"] is None:
        return None  # publicado como ausente pela própria fonte

    try:
        valor = float(ponto["value"])
    except (TypeError, ValueError) as exc:
        raise FonteWorldBankError(f"valor não numérico da fonte: {ponto['value']!r}") from exc

    pais = ponto.get("country") or {}
    return ObservacaoGlobal(
        indicador=indicador,
        nome_do_indicador=str(config["nome"]),
        pais_iso3=str(ponto.get("countryiso3code") or pais_iso3).upper(),
        nome_do_pais=str(pais.get("value", "")),
        ano=str(ponto.get("date", ano)),
        valor=valor,
        unidade=str(config["unidade"]),
        periodicidade=str(config["periodicidade"]),
        licenca=LICENCA,
        atribuicao=ATRIBUICAO,
    )
