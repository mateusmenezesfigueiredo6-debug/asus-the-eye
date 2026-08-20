# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Funil de oportunidades — append-only, com transições válidas e auditáveis.

Uma oportunidade nunca é editada no lugar: cada mudança de estágio é um evento
novo, exatamente como o ledger de auditoria. Isso permite reconstruir o funil em
qualquer data passada e medir tempo de ciclo por estágio de verdade, em vez de
inferi-lo do último carimbo.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGES = ("entrada", "qualificacao", "proposta", "negociacao", "ganho", "perdido")
OPEN_STAGES = ("entrada", "qualificacao", "proposta", "negociacao")
CLOSED_STAGES = ("ganho", "perdido")

# Transições permitidas. Voltar um estágio é legítimo (a negociação esfriou);
# pular direto de entrada para ganho não é — sem proposta não há o que ganhar.
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "entrada": ("qualificacao", "perdido"),
    "qualificacao": ("proposta", "entrada", "perdido"),
    "proposta": ("negociacao", "qualificacao", "ganho", "perdido"),
    "negociacao": ("ganho", "perdido", "proposta"),
    "ganho": (),
    "perdido": (),
}

LOST_REASONS = (
    "preco",
    "prazo",
    "escopo",
    "concorrencia",
    "sem_resposta",
    "desistiu",
    "fora_de_escopo",
    "outro",
)
SOURCE_CHANNELS = (
    "indicacao",
    "site",
    "evento",
    "prospeccao_ativa",
    "recorrencia",
    "parceria",
    "outro",
)
ENGAGEMENT_MODELS = ("exito", "hora", "fixo", "misto")


class OpportunityError(RuntimeError):
    """Transição ou dado inválido no funil."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pseudonymize(client_identifier: str, salt: str = "commercial") -> str:
    """Referência estável e irreversível do cliente.

    O nome real nunca é gravado: o operador vê o rótulo que digitou na tela, o
    registro guarda só o pseudônimo. Mesmo cliente sempre dá a mesma referência.
    """
    digest = hashlib.sha256(f"{salt}:{client_identifier.strip().lower()}".encode()).hexdigest()
    return f"cli-{digest[:16]}"


def new_opportunity(
    *,
    niche_id: str,
    client_identifier: str,
    source_channel: str,
    client_type: str = "empresa",
    legal_area_ids: list[str] | None = None,
    engagement_model: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if source_channel not in SOURCE_CHANNELS:
        raise OpportunityError(f"canal desconhecido: {source_channel!r}")
    if engagement_model and engagement_model not in ENGAGEMENT_MODELS:
        raise OpportunityError(f"modelo de contratação desconhecido: {engagement_model!r}")
    now = _now()
    return {
        "opportunity_id": str(uuid.uuid4()),
        "niche_id": niche_id,
        "legal_area_ids_suggested": legal_area_ids or [],
        "client_ref_pseudonymous": pseudonymize(client_identifier),
        "client_type": client_type,
        "stage": "entrada",
        "source_channel": source_channel,
        "engagement_model": engagement_model,
        "value_brl": None,
        "probability_declared": None,
        "created_at": now,
        "updated_at": now,
        "notes_hash_sha256": hashlib.sha256(notes.encode()).hexdigest() if notes else None,
        "claim_class": "FACT",
    }


class Pipeline:
    """Funil persistido em JSONL append-only."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------- leitura

    def _records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def opportunities(self, as_of: str | None = None) -> list[dict[str, Any]]:
        """Estado atual (ou em qualquer data passada) de cada oportunidade."""
        current: dict[str, dict[str, Any]] = {}
        for record in self._records():
            if as_of and record["updated_at"] > as_of:
                continue
            current[record["opportunity_id"]] = record
        return list(current.values())

    def history(self, opportunity_id: str) -> list[dict[str, Any]]:
        return [r for r in self._records() if r["opportunity_id"] == opportunity_id]

    def get(self, opportunity_id: str) -> dict[str, Any]:
        records = self.history(opportunity_id)
        if not records:
            raise OpportunityError(f"oportunidade inexistente: {opportunity_id}")
        return records[-1]

    # ------------------------------------------------------------- escrita

    def _append(self, record: dict[str, Any]) -> dict[str, Any]:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def add(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        return self._append(opportunity)

    def advance(
        self,
        opportunity_id: str,
        to_stage: str,
        *,
        lost_reason: str | None = None,
        value_brl: float | None = None,
        probability_declared: float | None = None,
    ) -> dict[str, Any]:
        """Move a oportunidade. Cada movimento é um registro novo, nunca uma edição."""
        current = self.get(opportunity_id)
        from_stage = current["stage"]
        if to_stage not in STAGES:
            raise OpportunityError(f"estágio desconhecido: {to_stage!r}")
        if to_stage not in ALLOWED_TRANSITIONS[from_stage]:
            allowed = ALLOWED_TRANSITIONS[from_stage] or ("nenhum — estágio final",)
            raise OpportunityError(f"transição inválida {from_stage!r} → {to_stage!r}; permitidas: {allowed}")
        if to_stage == "perdido":
            if lost_reason not in LOST_REASONS:
                raise OpportunityError("perder exige motivo registrado — perder sem motivo não ensina nada")
        if to_stage == "ganho":
            declared = value_brl if value_brl is not None else current.get("value_brl")
            if declared is None:
                raise OpportunityError("ganhar exige o valor registrado da proposta")

        now = _now()
        updated = {
            **current,
            "stage": to_stage,
            "updated_at": now,
        }
        if lost_reason:
            updated["lost_reason"] = lost_reason
        if value_brl is not None:
            updated["value_brl"] = value_brl
        if probability_declared is not None:
            updated["probability_declared"] = probability_declared
        if to_stage in CLOSED_STAGES:
            updated["closed_at"] = now
        return self._append(updated)
