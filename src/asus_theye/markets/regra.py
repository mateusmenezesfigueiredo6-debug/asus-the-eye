# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regra de resolução estruturada — legível por máquina, e **executável**.

Até aqui o critério de um claim vivia em prosa: ``"IPCA mensal >= 0.50%"``. Um
humano entende; um programa não consegue verificar. Pior: a prosa e o código que
liquida são duas fontes de verdade que podem divergir em silêncio — o texto diz
``>=`` e o comparador poderia dizer ``>``, e nada acusaria.

Aqui a regra deixa de ser decoração. Ela é um bloco declarado no claim que esta
biblioteca sabe **avaliar**, e o resolvedor liquida chamando :func:`avaliar` —
de modo que o texto, a estrutura e o desfecho não são três coisas que precisam
concordar, e sim uma só. O texto humano passa a ser **derivado** da estrutura,
nunca digitado ao lado dela.

Separa "mercado" de "aposta": um mercado tem regra verificável; uma aposta tem
alguém decidindo depois quem ganhou.
"""

from __future__ import annotations

import re
from typing import Any

VERSAO_SCHEMA = 1

MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Os únicos comparadores admitidos. Igualdade exata não entra: valor de fonte
# oficial é decimal arredondado, e "== 0,50" seria uma armadilha de precisão
# disfarçada de regra.
OPERADORES: dict[str, Any] = {
    ">=": lambda valor, limiar: valor >= limiar,
    ">": lambda valor, limiar: valor > limiar,
    "<=": lambda valor, limiar: valor <= limiar,
    "<": lambda valor, limiar: valor < limiar,
}

# Como o número se lê. A unidade não é enfeite: 14,00 em `percentual_anual`
# (Selic) e 14,00 em `brl` (câmbio) são perguntas completamente diferentes.
UNIDADES = {
    "percentual_mensal": "%",
    "percentual_anual": "% a.a.",
    "brl": "R$",
}

CAMPOS = (
    "versao_schema",
    "fonte",
    "serie",
    "indicador",
    "periodo_referencia",
    "operador",
    "limiar",
    "unidade",
    "quando_indisponivel",
)

# A única política admitida para valor ausente. Escrita como campo, e não como
# comportamento implícito, porque é a regra que mais tenta ser violada sob
# pressão: fonte muda, alguém "resolve" com zero, e o Brier vira ficção.
INDISPONIVEL_UNKNOWN = "UNKNOWN"


class RegraError(RuntimeError):
    """Regra malformada. Sempre levanta — claim sem regra verificável não entra."""


def montar_regra(
    *,
    fonte: str,
    serie: int,
    indicador: str,
    periodo_referencia: str,
    limiar: float,
    unidade: str,
    operador: str = ">=",
) -> dict[str, Any]:
    """Constrói a regra e a valida. Nunca devolve regra que não passe no schema."""
    regra = {
        "versao_schema": VERSAO_SCHEMA,
        "fonte": fonte,
        "serie": int(serie),
        "indicador": indicador,
        "periodo_referencia": periodo_referencia,
        "operador": operador,
        "limiar": float(limiar),
        "unidade": unidade,
        "quando_indisponivel": INDISPONIVEL_UNKNOWN,
    }
    validar_regra(regra)
    return regra


def validar_regra(regra: Any) -> dict[str, Any]:
    """Valida a regra contra o schema. Levanta :class:`RegraError` no primeiro erro."""
    if not isinstance(regra, dict):
        raise RegraError(f"regra deve ser objeto, veio {type(regra).__name__}")

    faltando = [campo for campo in CAMPOS if campo not in regra]
    if faltando:
        raise RegraError(f"regra sem campo(s) obrigatório(s): {faltando}")

    if regra["versao_schema"] != VERSAO_SCHEMA:
        raise RegraError(f"versao_schema desconhecida: {regra['versao_schema']!r} (esperada {VERSAO_SCHEMA})")

    if regra["operador"] not in OPERADORES:
        raise RegraError(f"operador {regra['operador']!r} não admitido; use um de {sorted(OPERADORES)}")

    if regra["unidade"] not in UNIDADES:
        raise RegraError(f"unidade {regra['unidade']!r} não admitida; use uma de {sorted(UNIDADES)}")

    limiar = regra["limiar"]
    if not isinstance(limiar, (int, float)) or isinstance(limiar, bool):
        raise RegraError(f"limiar deve ser número, veio {limiar!r}")

    if not isinstance(regra["serie"], int) or isinstance(regra["serie"], bool):
        raise RegraError(f"serie deve ser inteiro (identificador na fonte), veio {regra['serie']!r}")

    for campo in ("fonte", "indicador"):
        if not str(regra[campo]).strip():
            raise RegraError(f"{campo} vazio — regra sem proveniência não é verificável")

    if not MES_RE.fullmatch(str(regra["periodo_referencia"])):
        raise RegraError(f"periodo_referencia deve ser 'aaaa-mm', veio {regra['periodo_referencia']!r}")

    if regra["quando_indisponivel"] != INDISPONIVEL_UNKNOWN:
        raise RegraError(
            f"quando_indisponivel deve ser {INDISPONIVEL_UNKNOWN!r}, veio {regra['quando_indisponivel']!r} "
            "— valor ausente NUNCA vira desfecho; liquidar sem dado é fabricar Brier"
        )

    from asus_theye.markets.claim import _is_forbidden

    if _is_forbidden(str(regra["fonte"])):
        raise RegraError(f"fonte {regra['fonte']!r} proibida — comparador nunca resolve")

    return regra


def avaliar(regra: dict[str, Any], valor: float | None) -> int | None:
    """Aplica a regra ao valor da fonte. ``None`` significa UNKNOWN, nunca zero.

    Esta é a função que o resolvedor chama. Ter uma só implementação do
    comparador é o que impede a prosa do critério e o desfecho de divergirem.
    """
    validar_regra(regra)
    if valor is None:
        return None
    return int(OPERADORES[regra["operador"]](float(valor), float(regra["limiar"])))


def texto(regra: dict[str, Any]) -> str:
    """Frase humana DERIVADA da estrutura — para que as duas não possam divergir."""
    validar_regra(regra)
    simbolo = UNIDADES[regra["unidade"]]
    limiar = float(regra["limiar"])
    valor = f"R$ {limiar:.2f}" if regra["unidade"] == "brl" else f"{limiar:.2f}{simbolo}"
    return f"{regra['indicador']} {regra['operador']} {valor} ({regra['periodo_referencia']}, fonte: {regra['fonte']})"
