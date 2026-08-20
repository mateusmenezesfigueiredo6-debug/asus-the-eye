# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Extrato mensal em Markdown da atividade real da plataforma."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asus_theye.projeto.medicao import MedicaoError, medir_projeto

_MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_MES_PREFIXO_RE = re.compile(r"^(\d{4}-\d{2})")


def _json(caminho: Path) -> dict[str, Any]:
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def _jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha.strip()]


def _mes_alvo(mes: str | None) -> str:
    if mes is None:
        return datetime.now(timezone.utc).strftime("%Y-%m")
    if not _MES_RE.fullmatch(mes):
        raise ValueError(f"mês inválido {mes!r}; use AAAA-MM")
    return mes


def _mes_do_valor(valor: object) -> str | None:
    if isinstance(valor, str):
        achado = _MES_PREFIXO_RE.match(valor)
        if achado:
            return achado.group(1)
    return None


def _filtrar_por_mes(registros: list[dict[str, Any]], *campos: str, mes: str) -> list[dict[str, Any]]:
    filtrados: list[dict[str, Any]] = []
    for registro in registros:
        for campo in campos:
            valor = registro.get(campo)
            if _mes_do_valor(valor) == mes:
                filtrados.append(registro)
                break
    return filtrados


def _fmt_float(valor: object) -> str:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return "—"
    return f"{float(valor):.4f}"


def _tabela(colunas: list[str], linhas: list[list[object]]) -> list[str]:
    if not linhas:
        return ["nenhum", ""]
    saida = [
        "| " + " | ".join(colunas) + " |",
        "| " + " | ".join("---" for _ in colunas) + " |",
    ]
    for linha in linhas:
        saida.append("| " + " | ".join(str(valor) for valor in linha) + " |")
    saida.append("")
    return saida


def _hash_da_medicao(base: Path) -> str | None:
    try:
        return str(medir_projeto(base).get("hash_da_medicao") or "")
    except (KeyError, MedicaoError, TypeError, ValueError):
        return None


def relatorio_mensal(mes: str | None = None, base: Path = Path("reports")) -> str:
    """Devolve o extrato mensal em Markdown, só com o que os artefatos realmente dizem.

    A seção de mercados "ainda abertos" reflete o estado corrente em
    ``registro.json`` para os mercados emitidos no mês; ela não reconstrói
    estado a partir de outros artefatos.
    """
    mes_ref = _mes_alvo(mes)
    markets = base / "markets"
    mlops = base / "mlops"

    mercados = _json(markets / "registro.json").get("mercados", [])
    resolucoes = _filtrar_por_mes(_jsonl(markets / "resolucoes.jsonl"), "resolved_at", mes=mes_ref)
    divergencias = _filtrar_por_mes(_jsonl(markets / "comparador.jsonl"), "recorded_at", mes=mes_ref)
    eventos = _filtrar_por_mes(_jsonl(markets / "eventos.jsonl"), "recorded_at", "occurred_at", mes=mes_ref)
    ancoras = _filtrar_por_mes(_jsonl(markets / "ancoras.jsonl"), "registrado_em", mes=mes_ref)
    corridas = _filtrar_por_mes(_jsonl(mlops / "corridas.jsonl"), "executada_em", mes=mes_ref)
    emitidos_no_mes = _filtrar_por_mes(mercados, "created_at", mes=mes_ref)
    emitidos_no_mes_ainda_abertos = [mercado for mercado in emitidos_no_mes if mercado.get("estado") != "LIQUIDADO"]

    linhas = [
        f"# Relatório mensal da plataforma — {mes_ref}",
        "",
        "## Resumo",
        "",
        f"- Mercados emitidos no mês: {len(emitidos_no_mes)} | liquidações no mês: {len(resolucoes)}",
        (
            f"- Mercados emitidos no mês ainda abertos: {len(emitidos_no_mes_ainda_abertos)} | "
            f"divergências medidas: {len(divergencias)}"
        ),
        f"- Eventos selados: {len(eventos)} | âncoras: {len(ancoras)} | corridas MLOps: {len(corridas)}",
        "",
        "## Liquidações do mês",
        "",
    ]
    linhas.extend(
        _tabela(
            ["claim", "desfecho", "Brier", "fonte"],
            [
                [
                    resolucao.get("claim_id", "—"),
                    resolucao.get("outcome", "—"),
                    _fmt_float(resolucao.get("brier_do_contrato")),
                    resolucao.get("resolution_source", "—"),
                ]
                for resolucao in resolucoes
            ],
        )
    )
    linhas.extend(["## Mercados emitidos no mês ainda abertos", ""])
    linhas.extend(
        _tabela(
            ["claim", "área", "estado", "p", "criado_em"],
            [
                [
                    mercado.get("claim_id", "—"),
                    mercado.get("market_area_id", "—"),
                    mercado.get("estado", "—"),
                    _fmt_float(mercado.get("probability")),
                    mercado.get("created_at", "—"),
                ]
                for mercado in emitidos_no_mes_ainda_abertos
            ],
        )
    )
    linhas.extend(["## Divergências do mês", ""])
    linhas.extend(
        _tabela(
            ["claim", "comparador", "preço", "nossa p", "divergência", "ticker"],
            [
                [
                    divergencia.get("claim_id", "—"),
                    divergencia.get("comparator", "—"),
                    _fmt_float(divergencia.get("comparator_price")),
                    _fmt_float(divergencia.get("our_probability")),
                    _fmt_float(divergencia.get("divergence")),
                    divergencia.get("ticker", "—"),
                ]
                for divergencia in divergencias
            ],
        )
    )
    linhas.extend(["## Eventos selados do mês", ""])
    linhas.extend(
        _tabela(
            ["seq", "tipo", "correlação", "hash"],
            [
                [
                    evento.get("sequence", "—"),
                    evento.get("event_type", "—"),
                    evento.get("correlation_id", "—"),
                    evento.get("event_hash_sha256", "—"),
                ]
                for evento in eventos
            ],
        )
    )
    linhas.extend(["## Âncoras do mês", ""])
    linhas.extend(
        _tabela(
            ["merkle_root", "tx_hash", "rede", "registrado_em"],
            [
                [
                    ancora.get("manifest", {}).get("merkle_root", "—"),
                    ancora.get("ancora", {}).get("tx_hash", "—"),
                    ancora.get("ancora", {}).get("chain_id", "—"),
                    ancora.get("registrado_em", "—"),
                ]
                for ancora in ancoras
            ],
        )
    )
    linhas.extend(["## Corridas MLOps do mês", ""])
    linhas.extend(
        _tabela(
            ["modelo", "versão", "estado", "executada_em"],
            [
                [
                    corrida.get("modelo_id", "—"),
                    corrida.get("versao", "—"),
                    corrida.get("estado", "—"),
                    corrida.get("executada_em", "—"),
                ]
                for corrida in corridas
            ],
        )
    )

    rodape = "© 2026 Mateus Menezes Figueiredo · AGPL-3.0"
    hash_medicao = _hash_da_medicao(base)
    if hash_medicao:
        rodape = f"{rodape} · hash da medição: `{hash_medicao}`"
    linhas.extend(["---", rodape, ""])
    return "\n".join(linhas)
