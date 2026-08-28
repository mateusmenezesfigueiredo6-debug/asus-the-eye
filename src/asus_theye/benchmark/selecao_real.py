# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ponte da seleção de carteira para os mercados REAIS do registro.

Honestidade primeiro (UNKNOWN over guess):

- "Edge" de verdade é `p_nosso − p_comparador`. Se o comparador (Kalshi) não
  tem cotação registrada para o mercado, edge NÃO existe — e este módulo não
  inventa. Nesse caso a seleção roda em modo **confianca**: o valor de cada
  mercado é `|2p − 1|` (a convicção declarada do gerador), rotulado como valor
  EDITORIAL — serve para escolher o que publicar em destaque, nunca como
  vantagem sobre mercado.
- Correlação entre mercados não é medida hoje: entra como 0 e a limitação fica
  DECLARADA no resultado, não escondida.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .selecao_carteira import Candidato

REGISTRO_PADRAO = Path("reports/markets/registro.json")
COMPARADOR_PADRAO = Path("reports/markets/comparador.jsonl")


def _cotacoes_do_comparador(caminho: Path) -> dict[str, float]:
    """Última cotação do comparador por claim_id (arquivo pode não existir)."""

    cotacoes: dict[str, float] = {}
    if not caminho.exists():
        return cotacoes
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            registro = json.loads(linha)
        except json.JSONDecodeError:
            continue
        claim = registro.get("claim_id")
        preco = registro.get("comparator_price", registro.get("p_comparador"))
        if isinstance(claim, str) and isinstance(preco, (int, float)) and math.isfinite(preco):
            cotacoes[claim] = float(preco)
    return cotacoes


def carregar_candidatos_reais(
    registro: Path = REGISTRO_PADRAO,
    comparador: Path = COMPARADOR_PADRAO,
) -> tuple[list[Candidato], dict[tuple[int, int], float], dict[str, Any]]:
    """Converte os mercados ABERTOS do registro em candidatos da seleção.

    Devolve (candidatos, correlação, diagnóstico). O diagnóstico declara o modo
    (edge/confianca) e toda limitação de dado — quem consome decide com os
    olhos abertos.
    """

    dados = json.loads(Path(registro).read_text(encoding="utf-8"))
    abertos = [m for m in dados.get("mercados", []) if m.get("estado") == "ABERTO"]
    if not abertos:
        raise ValueError("registro não tem mercado ABERTO — nada a selecionar")

    cotacoes = _cotacoes_do_comparador(Path(comparador))
    com_comparador = [m for m in abertos if m.get("claim_id") in cotacoes]
    modo = "edge" if len(com_comparador) == len(abertos) else "confianca"

    candidatos: list[Candidato] = []
    for mercado in abertos:
        claim = str(mercado.get("claim_id"))
        p = mercado.get("probability")
        if not isinstance(p, (int, float)) or not 0.0 <= float(p) <= 1.0:
            raise ValueError(f"{claim}: probability inválida no registro")
        if modo == "edge":
            valor = float(p) - cotacoes[claim]
        else:
            valor = abs(2.0 * float(p) - 1.0)
        candidatos.append(
            Candidato(
                codigo=claim,
                edge=round(valor, 6),
                risco=0.0,
                descricao=str(mercado.get("question", ""))[:80],
            )
        )

    diagnostico = {
        "modo": modo,
        "mercados_abertos": len(abertos),
        "com_comparador": len(com_comparador),
        "limitacoes": [
            (
                "edge real indisponível: comparador sem cotação para "
                f"{len(abertos) - len(com_comparador)} de {len(abertos)} mercados; "
                "valor = |2p−1| (convicção editorial, NÃO é vantagem sobre mercado)"
            )
            if modo == "confianca"
            else "edge = p_nosso − p_comparador (última cotação registrada)",
            "correlação entre mercados não medida: tratada como 0 (penalidade inerte)",
            "risco por posição não medido: tratado como 0",
        ],
    }
    return candidatos, {}, diagnostico
