# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""M4 — divergência vs comparador (Chaox) MEDIDA e SELADA de verdade.

O instrumento existia (:func:`asus_theye.markets.resolution.record_comparator`)
com ZERO medições — os "66,7%" que circulavam saíam de demo com números à mão.
Este módulo faz a medição real existir, com as regras de sempre:

1. **Chaox é comparador, NUNCA resolutor.** O preço dela é opinião agregada;
   entra aqui só para registrar ONDE discordamos. Quem acertou só se sabe
   depois que o claim liquidar contra a fonte oficial — e o texto do evento
   selado carrega essa régua.
2. **Mapeamento declarado ou nada.** Comparar IPCA (BR) com um mercado de CPI
   (EUA) é comparável INDIRETO: a ``nota_de_mapeamento`` é obrigatória e vai
   selada junto — comparação sem declarar a diferença é meia-verdade.
3. **Identidade = conteúdo declarado, sem relógio** (lição do mlops): a mesma
   observação (claim, comparador, preço, nossa probabilidade) deduplica; preço
   novo é observação nova. ``recorded_at`` viaja no conteúdo mas fica FORA da
   identidade — no dedupe, sela-se o registro JÁ armazenado.
4. **Sela PRIMEIRO, apenda DEPOIS, sob trava** — store versionado
   ``reports/markets/comparador.jsonl`` no padrão append-only auto-reparador.
"""

from __future__ import annotations

import fcntl
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import hash_json
from asus_theye.audit.sdk import AuditSDK
from asus_theye.markets.claim import MarketClaim, make_claim
from asus_theye.markets.resolution import record_comparator

COMPARADOR_PADRAO = Path("reports/markets/comparador.jsonl")


class ComparadorError(RuntimeError):
    """Observação inválida, claim desconhecido ou divergência de conteúdo. Sempre levanta."""


@contextmanager
def _trava(arquivo: Path) -> Iterator[None]:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.with_name(".lock-comparador").open("a+", encoding="utf-8") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)


def _linhas(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def _claim_do_registro(mercado: dict[str, Any]) -> MarketClaim:
    """Reconstrói o claim tipado a partir da linha do registro de mercados."""
    return make_claim(
        claim_id=str(mercado["claim_id"]),
        market_area_id=str(mercado["market_area_id"]),
        question=str(mercado["question"]),
        deadline=str(mercado["deadline"]),
        probability=float(mercado["probability"]),
        created_at=str(mercado["created_at"]),
    )


def observar_divergencia(
    *,
    claim_id: str,
    comparator_price: float,
    ticker: str,
    nota_de_mapeamento: str,
    comparator: str = "Chaox",
    store: Path = Path("reports/markets/registro.json"),
    arquivo: Path = COMPARADOR_PADRAO,
    sdk: AuditSDK | None = None,
    eventos: Path | None = None,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Mede e SELA a divergência entre a nossa probabilidade e o preço do comparador.

    Levanta se o claim não existe no registro, se a nota de mapeamento está
    vazia (comparável indireto sem declaração é meia-verdade) ou se o ticker
    não vem nomeado (proveniência).
    """
    if not nota_de_mapeamento.strip():
        raise ComparadorError(
            f"{claim_id}: nota_de_mapeamento é obrigatória — declarar O QUE o ticker mede e "
            "por que é comparável (direto ou indireto) faz parte da medição"
        )
    if not ticker.strip():
        raise ComparadorError(f"{claim_id}: ticker do comparador é obrigatório (proveniência do preço)")
    if not store.exists():
        raise ComparadorError(f"registro de mercados ausente: {store}")
    mercados = json.loads(store.read_text(encoding="utf-8")).get("mercados", [])
    mercado = next((m for m in mercados if m.get("claim_id") == claim_id), None)
    if mercado is None:
        raise ComparadorError(f"{claim_id}: claim não existe no registro — divergência de mercado fantasma não entra")

    divergencia = record_comparator(
        _claim_do_registro(mercado),
        comparator_price=comparator_price,
        comparator=comparator,
        recorded_at=recorded_at,
    )
    registro = divergencia.as_dict() | {"ticker": ticker, "nota_de_mapeamento": nota_de_mapeamento}
    identidade = {
        "claim_id": registro["claim_id"],
        "comparator": registro["comparator"],
        "comparator_price": registro["comparator_price"],
        "our_probability": registro["our_probability"],
        "ticker": ticker,
    }
    registro["observacao_id"] = hash_json(identidade)

    with _trava(arquivo):
        existente = next((li for li in _linhas(arquivo) if li.get("observacao_id") == registro["observacao_id"]), None)
        vigente = existente if existente is not None else registro
        selagem = None
        if sdk is not None:
            from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

            selagem = selar_registro(
                sdk,
                vigente,
                tipo_evento="market.comparator",
                recurso="comparator",
                correlation_id=f"comparador:{registro['observacao_id'][:32]}",
                occurred_at=str(vigente.get("recorded_at") or ""),
                eventos=eventos or EVENTOS_PADRAO,
            )
        if existente is None:
            with arquivo.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return {"registro": vigente, "duplicate": existente is not None, "selagem": selagem}
