# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Consolidado anual em Markdown da atividade real da plataforma."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .mensal import _fmt_float, _hash_da_medicao, _json, _jsonl, _tabela

_ANO_RE = re.compile(r"^\d{4}$")
_ANO_PREFIXO_RE = re.compile(r"^(\d{4})")


def _ano_alvo(ano: str | None) -> str:
    if ano is None:
        return datetime.now(timezone.utc).strftime("%Y")
    if not _ANO_RE.fullmatch(ano):
        raise ValueError(f"ano inválido {ano!r}; use AAAA")
    return ano


def _ano_do_valor(valor: object) -> str | None:
    if isinstance(valor, str):
        achado = _ANO_PREFIXO_RE.match(valor)
        if achado:
            return achado.group(1)
    return None


def _filtrar_por_ano(registros: list[dict[str, Any]], *campos: str, ano: str) -> list[dict[str, Any]]:
    filtrados: list[dict[str, Any]] = []
    for registro in registros:
        for campo in campos:
            if _ano_do_valor(registro.get(campo)) == ano:
                filtrados.append(registro)
                break
    return filtrados


def _claim_ids_retrospectivos(retrospectivos: list[dict[str, Any]]) -> set[str]:
    return {str(item["claim_id"]) for item in retrospectivos if item.get("claim_id")}


def _fontes_area(resolucoes: list[dict[str, Any]], area: str) -> str:
    fontes = sorted(
        {
            str(resolucao.get("resolution_source"))
            for resolucao in resolucoes
            if resolucao.get("market_area_id") == area and resolucao.get("resolution_source")
        }
    )
    if not fontes:
        return "—"
    return "; ".join(fontes)


def _media_brier_area(resolucoes: list[dict[str, Any]], area: str) -> float | None:
    briers = [
        float(resolucao["brier_do_contrato"])
        for resolucao in resolucoes
        if resolucao.get("market_area_id") == area
        and isinstance(resolucao.get("brier_do_contrato"), (int, float))
        and not isinstance(resolucao.get("brier_do_contrato"), bool)
    ]
    if not briers:
        return None
    return sum(briers) / len(briers)


def _nota_retrospectivos(retrospectivos: list[dict[str, Any]]) -> str:
    total = len(retrospectivos)
    if total == 0:
        return "- Nenhuma reconstrução retrospectiva do acervo legado apareceu neste ano."
    substantivo = "reconstrução retrospectiva" if total == 1 else "reconstruções retrospectivas"
    verbo = "ficou" if total == 1 else "ficaram"
    return (
        f"- {total} {substantivo} em `reports/markets/legado_retrospectivo.jsonl` "
        f"{verbo} fora deste consolidado: são inelegíveis como previsão."
    )


def relatorio_anual(ano: str | None = None, base: Path = Path("reports")) -> str:
    """Devolve o consolidado anual em Markdown, sem atribuir skill não medida."""

    ano_ref = _ano_alvo(ano)
    markets = base / "markets"
    mlops = base / "mlops"

    mercados = _json(markets / "registro.json").get("mercados", [])
    retrospectivos = _filtrar_por_ano(
        _jsonl(markets / "legado_retrospectivo.jsonl"),
        "resolved_at",
        "created_at",
        "quoted_at",
        ano=ano_ref,
    )
    claim_ids_excluidos = _claim_ids_retrospectivos(retrospectivos)

    emitidos = [
        mercado
        for mercado in _filtrar_por_ano(mercados, "created_at", ano=ano_ref)
        if str(mercado.get("claim_id", "")) not in claim_ids_excluidos
    ]
    resolucoes_brutas = _filtrar_por_ano(_jsonl(markets / "resolucoes.jsonl"), "resolved_at", ano=ano_ref)
    area_por_claim = {
        str(mercado.get("claim_id")): str(mercado.get("market_area_id"))
        for mercado in mercados
        if mercado.get("claim_id") and mercado.get("market_area_id")
    }
    for retrospectivo in retrospectivos:
        if retrospectivo.get("claim_id") and retrospectivo.get("market_area_id"):
            area_por_claim[str(retrospectivo["claim_id"])] = str(retrospectivo["market_area_id"])

    resolucoes: list[dict[str, Any]] = []
    for resolucao in resolucoes_brutas:
        claim_id = str(resolucao.get("claim_id", ""))
        if claim_id in claim_ids_excluidos:
            continue
        enriquecida = dict(resolucao)
        if not enriquecida.get("market_area_id"):
            enriquecida["market_area_id"] = area_por_claim.get(claim_id, "—")
        resolucoes.append(enriquecida)

    eventos = _filtrar_por_ano(_jsonl(markets / "eventos.jsonl"), "recorded_at", "occurred_at", ano=ano_ref)
    ancoras = _filtrar_por_ano(_jsonl(markets / "ancoras.jsonl"), "registrado_em", ano=ano_ref)
    corridas = _filtrar_por_ano(_jsonl(mlops / "corridas.jsonl"), "executada_em", ano=ano_ref)

    areas: list[str] = []
    for mercado in emitidos:
        area = mercado.get("market_area_id")
        if isinstance(area, str) and area and area not in areas:
            areas.append(area)
    for resolucao in resolucoes:
        area = resolucao.get("market_area_id")
        if isinstance(area, str) and area and area not in areas:
            areas.append(area)

    linhas = [
        f"# Relatório anual da plataforma — {ano_ref}",
        "",
        "## Resumo",
        "",
        f"- Mercados emitidos no ano: {len(emitidos)} | liquidações elegíveis no ano: {len(resolucoes)}",
        f"- Eventos selados: {len(eventos)} | âncoras: {len(ancoras)} | corridas MLOps: {len(corridas)}",
        "",
        "## Brier médio por área (somente liquidados elegíveis)",
        "",
    ]
    linhas.extend(
        _tabela(
            ["área", "n", "Brier médio", "fontes oficiais"],
            [
                [
                    area,
                    sum(1 for resolucao in resolucoes if resolucao.get("market_area_id") == area),
                    _fmt_float(_media_brier_area(resolucoes, area)),
                    _fontes_area(resolucoes, area),
                ]
                for area in areas
            ],
        )
    )
    linhas.extend(
        [
            "## O que este relatório NÃO afirma",
            "",
            "- Brier médio de poucos contratos liquidados não demonstra skill por si só.",
            (
                "- Skill exige baseline explícito e janela declarada; sem isso, "
                "o número não prova vantagem sobre um palpite constante "
                "(ver `markets/scoring.py`)."
            ),
            "- Contrato aberto não entra em Brier; ausência de liquidação não é acerto nem erro medido.",
            "",
            "## Nota sobre o acervo legado",
            "",
        ]
    )
    linhas.append(_nota_retrospectivos(retrospectivos))
    linhas.extend(["", "---"])

    rodape = "© 2026 Mateus Menezes Figueiredo · AGPL-3.0"
    hash_medicao = _hash_da_medicao(base)
    if hash_medicao:
        rodape = f"{rodape} · hash da medição: `{hash_medicao}`"
    linhas.extend([rodape, ""])
    return "\n".join(linhas)
