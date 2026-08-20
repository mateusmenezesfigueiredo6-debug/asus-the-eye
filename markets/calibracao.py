# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Calibração — a probabilidade declarada vale alguma coisa?

Um Brier agregado esconde quase tudo. O mesmo 0,50 significa coisas muito
diferentes a três meses e na véspera, e um previsor pode ter Brier bom sendo
sistematicamente mal calibrado. Este módulo mede as três coisas que respondem
de verdade:

1. **Curva de confiabilidade** — quando dissemos 70%, aconteceu ~70% das vezes?
   A curva ideal é a diagonal; o desvio dela é o viés.
2. **Brier estratificado por horizonte** — o número só é interpretável cortado
   por tempo-até-o-desfecho.
3. **Decomposição de Murphy** — ``BS = confiabilidade − resolução + incerteza``.
   Separa "erra o nível" (confiabilidade) de "não distingue os casos"
   (resolução). Um previsor que sempre diz a taxa-base é perfeitamente
   confiável e completamente inútil; só a decomposição mostra isso.

**O horizonte é re-ancorado.** O ponto da série guarda o horizonte contra o
``deadline`` do contrato, que é um proxy. O horizonte que vale é o medido contra
``determination_date`` — quando a fonte oficial publicou. Pontos cuja base é
``desconhecida`` (import legado) são **excluídos**: sem saber quando a fonte
publicou, o horizonte é ficção com aparência de número.

**Recusa antes de enfeitar.** Abaixo da amostra mínima nada é agregado. Curva de
confiabilidade com poucos pontos é ruído desenhado com régua, e gráfico convence
mais do que merece.

A matemática aqui é de domínio público (Brier 1950; Murphy 1973) e está
reimplementada em ~40 linhas de stdlib — nenhuma dependência nova entra para
calcular média e diferença ao quadrado.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

SERIE_PADRAO = Path("reports/markets/serie_p.jsonl")
RESOLUCOES_PADRAO = Path("reports/markets/resolucoes.jsonl")

# Curva de confiabilidade com poucos pares é ruído desenhado com régua. O corte
# é alto de propósito: estimar frequência observada por faixa exige pontos EM
# CADA faixa, não no total. Declarado, não escondido.
AMOSTRA_MINIMA = 30
# Mínimo por faixa para a faixa ser reportada — abaixo disso ela sai como None.
MINIMO_POR_FAIXA = 5

# Faixas de probabilidade da curva. Cortes nossos, escolhidos para que 0,50
# (o prior de máxima incerteza deste projeto) caia no MEIO de uma faixa e não
# na fronteira entre duas.
FAIXAS_P = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0))

# Faixas de horizonte, em dias até a determinação. Cortes nossos: refletem o
# calendário de divulgação brasileiro (mensal), não o de outra economia.
FAIXAS_HORIZONTE = (
    ("ate_7d", 0, 7),
    ("8_a_30d", 8, 30),
    ("31_a_90d", 31, 90),
    ("mais_de_90d", 91, 10_000),
)


class CalibracaoError(RuntimeError):
    """Insumo corrompido. Sempre levanta — calibração não se inventa."""


def _jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def pares(
    *,
    serie: Path = SERIE_PADRAO,
    resolucoes: Path = RESOLUCOES_PADRAO,
) -> dict[str, Any]:
    """Cruza cada ponto de p(t) com o desfecho do seu claim, re-ancorando o horizonte.

    Devolve os pares utilizáveis e, separadamente, o motivo de cada exclusão —
    porque "por que sobrou tão pouco" é a pergunta que um auditor faz primeiro.
    """
    from asus_theye.markets.resolution import BASES_CONFIAVEIS

    por_claim = {str(li["claim_id"]): li for li in _jsonl(resolucoes) if li.get("outcome") is not None}

    utilizaveis: list[dict[str, Any]] = []
    excluidos = {"claim_sem_desfecho": 0, "sem_determination_date": 0, "base_nao_confiavel": 0}

    for ponto in _jsonl(serie):
        desfecho = por_claim.get(str(ponto.get("claim_id")))
        if desfecho is None:
            excluidos["claim_sem_desfecho"] += 1
            continue
        determinada = desfecho.get("determination_date")
        if not determinada:
            excluidos["sem_determination_date"] += 1
            continue
        if str(desfecho.get("determination_basis", "")) not in BASES_CONFIAVEIS:
            excluidos["base_nao_confiavel"] += 1
            continue
        try:
            horizonte = (date.fromisoformat(str(determinada)) - date.fromisoformat(str(ponto["observado_em"]))).days
        except (ValueError, TypeError) as exc:
            raise CalibracaoError(f"{ponto.get('claim_id')}: datas inválidas no par ({exc})") from exc

        utilizaveis.append(
            {
                "claim_id": str(ponto["claim_id"]),
                "market_area_id": str(ponto.get("market_area_id", "")),
                "probability": float(ponto["probability"]),
                "outcome": int(desfecho["outcome"]),
                "observado_em": str(ponto["observado_em"]),
                "determination_date": str(determinada),
                # o horizonte que VALE: contra a publicação da fonte, não contra
                # o fechamento do contrato
                "horizonte_dias": horizonte,
                "horizonte_ate_deadline": ponto.get("horizonte_dias"),
            }
        )
    return {"pares": utilizaveis, "excluidos": excluidos}


def _brier(itens: list[dict[str, Any]]) -> float | None:
    if not itens:
        return None
    return round(sum((float(i["probability"]) - int(i["outcome"])) ** 2 for i in itens) / len(itens), 4)


def curva_de_confiabilidade(itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Frequência observada por faixa de probabilidade declarada.

    Faixa com menos de :data:`MINIMO_POR_FAIXA` pares reporta ``None`` — uma
    frequência estimada com 2 casos não é uma frequência, é uma anedota.
    """
    curva = []
    for inicio, fim in FAIXAS_P:
        # a última faixa inclui 1.0; as demais são semiabertas
        na_faixa = [
            i
            for i in itens
            if inicio <= float(i["probability"]) < fim or (fim == 1.0 and float(i["probability"]) == 1.0)
        ]
        suficiente = len(na_faixa) >= MINIMO_POR_FAIXA
        curva.append(
            {
                "faixa": f"{inicio:.1f}–{fim:.1f}",
                "n": len(na_faixa),
                "p_media_declarada": round(sum(float(i["probability"]) for i in na_faixa) / len(na_faixa), 4)
                if na_faixa
                else None,
                "frequencia_observada": round(sum(int(i["outcome"]) for i in na_faixa) / len(na_faixa), 4)
                if suficiente
                else None,
                "suficiente": suficiente,
            }
        )
    return curva


def decomposicao_de_murphy(itens: list[dict[str, Any]]) -> dict[str, Any] | None:
    """``BS = confiabilidade − resolução + incerteza`` (Murphy, 1973).

    Sem isto o Brier é opaco. Um previsor que sempre diz a taxa-base tem
    confiabilidade perfeita e resolução zero: acerta o nível e não distingue
    caso nenhum. Só a decomposição separa as duas coisas.
    """
    if not itens:
        return None
    n = len(itens)
    taxa_base = sum(int(i["outcome"]) for i in itens) / n
    confiabilidade = 0.0
    resolucao = 0.0
    for inicio, fim in FAIXAS_P:
        na_faixa = [
            i
            for i in itens
            if inicio <= float(i["probability"]) < fim or (fim == 1.0 and float(i["probability"]) == 1.0)
        ]
        if not na_faixa:
            continue
        peso = len(na_faixa) / n
        p_media = sum(float(i["probability"]) for i in na_faixa) / len(na_faixa)
        o_media = sum(int(i["outcome"]) for i in na_faixa) / len(na_faixa)
        confiabilidade += peso * (p_media - o_media) ** 2
        resolucao += peso * (o_media - taxa_base) ** 2
    return {
        "confiabilidade": round(confiabilidade, 4),
        "resolucao": round(resolucao, 4),
        "incerteza": round(taxa_base * (1 - taxa_base), 4),
        "taxa_base": round(taxa_base, 4),
        "nota": "BS = confiabilidade − resolução + incerteza; confiabilidade menor é melhor, resolução maior é melhor",
    }


def medir(*, serie: Path = SERIE_PADRAO, resolucoes: Path = RESOLUCOES_PADRAO) -> dict[str, Any]:
    """Snapshot da calibração. Abaixo da amostra mínima, RECUSA agregar."""
    cruzamento = pares(serie=serie, resolucoes=resolucoes)
    itens = cruzamento["pares"]
    n = len(itens)

    snapshot: dict[str, Any] = {
        "versao": 1,
        "n": n,
        "amostra_minima": AMOSTRA_MINIMA,
        "excluidos": cruzamento["excluidos"],
        "metodo_do_horizonte": (
            "horizonte medido contra determination_date (quando a fonte publicou), não contra o "
            "deadline do contrato. Pontos com base 'desconhecida' (import legado) são EXCLUÍDOS: "
            "sem saber quando a fonte publicou, o horizonte é ficção com aparência de número."
        ),
    }

    if n < AMOSTRA_MINIMA:
        snapshot["suficiente"] = False
        snapshot["brier"] = None
        snapshot["curva"] = None
        snapshot["por_horizonte"] = None
        snapshot["por_area"] = None
        snapshot["murphy"] = None
        snapshot["metodo"] = (
            f"amostra insuficiente: {n} par(es) contra mínimo de {AMOSTRA_MINIMA}. Nada é agregado. "
            "Curva de confiabilidade com poucos pontos é ruído desenhado com régua, e gráfico "
            "convence mais do que merece — por isso ele não é desenhado."
        )
        return snapshot

    snapshot["suficiente"] = True
    snapshot["brier"] = _brier(itens)
    snapshot["curva"] = curva_de_confiabilidade(itens)
    snapshot["murphy"] = decomposicao_de_murphy(itens)
    snapshot["por_horizonte"] = [
        {
            "faixa": nome,
            "n": len([i for i in itens if inicio <= int(i["horizonte_dias"]) <= fim]),
            "brier": _brier([i for i in itens if inicio <= int(i["horizonte_dias"]) <= fim]),
        }
        for nome, inicio, fim in FAIXAS_HORIZONTE
    ]
    areas = sorted({str(i["market_area_id"]) for i in itens})
    snapshot["por_area"] = [
        {
            "area": area,
            "n": len([i for i in itens if i["market_area_id"] == area]),
            "brier": _brier([i for i in itens if i["market_area_id"] == area]),
        }
        for area in areas
    ]
    snapshot["metodo"] = (
        "Brier por par (p − desfecho)²; curva de confiabilidade por faixa de p; decomposição de "
        "Murphy (1973); estratificação por horizonte re-ancorado e por área de mercado."
    )
    return snapshot


def selar(sdk: Any, snapshot: dict[str, Any] | None = None, *, eventos: Path | None = None) -> dict[str, Any]:
    """Sela a medição de calibração. Mesmo conjunto de pares = dedupe."""
    from asus_theye.audit.schema import hash_json
    from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

    snap = snapshot or medir()
    identidade = hash_json({"n": snap["n"], "brier": snap["brier"]})
    return selar_registro(
        sdk,
        snap,
        tipo_evento="market.calibration",
        recurso="calibration",
        correlation_id=f"calibracao:{identidade[:32]}",
        eventos=eventos or EVENTOS_PADRAO,
    )
