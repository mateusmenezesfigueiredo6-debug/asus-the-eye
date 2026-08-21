# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Score da Phase C — com evidência, sem imputação, sem preenchimento.

Três regras estruturais, cada uma fechando um jeito diferente de o score mentir:

1. **Sem imputação.** Componente sem dado é *omitido*, nunca zerado. Zerar é uma
   inferência disfarçada de medição. O omitido vira uma linha em ``limitations``.
2. **Denominador visível.** O score é média ponderada **só dos componentes
   presentes**, e ``components_present``/``components_declared`` viajam junto.
   Um score de 3-de-7 nunca pode ser lido como comparável a um de 7-de-7.
3. **Sem preenchimento.** ``build_ranking`` devolve o que existe.
   ``qualified_count`` é o real; ``padded`` é ``const: false`` no schema.

E uma quarta, que não é sobre score e sim sobre quem: ranquear pessoas é L4 e
exige DPIA humana, então o pipeline **recusa** materializar ``entity_type``
``person`` — mesmo o schema o prevendo para o futuro.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from asus_theye._pkg_paths import pkg_data

DATA_DIR = pkg_data("data", "source-graph")

CONFIDENCE_BY_COVERAGE = (
    (1.0, "high"),
    (0.7, "medium"),
    (0.4, "low"),
)


class ScoringError(RuntimeError):
    """Entrada inválida para o score. Sempre levanta — nunca degrada em silêncio."""


def load_weights() -> dict[str, float]:
    weights = json.loads((DATA_DIR / "ranking_weights.json").read_text(encoding="utf-8"))["weights"]
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ScoringError(f"pesos devem somar 1.0, somam {total}")
    return weights


def methodology_version() -> str:
    return json.loads((DATA_DIR / "ranking_weights.json").read_text(encoding="utf-8"))["methodology_version"]


def _validate_component(component: dict[str, Any], weights: dict[str, float]) -> None:
    component_id = component.get("component_id")
    if component_id not in weights:
        raise ScoringError(
            f"component_id desconhecido: {component_id!r}. "
            f"Enum fechado — métricas sociais (seguidores, engajamento) levantam aqui "
            f"em vez de serem silenciosamente ignoradas."
        )
    value = component.get("value")
    if not isinstance(value, int | float) or not 0.0 <= float(value) <= 1.0:
        raise ScoringError(f"{component_id}: value deve estar em [0,1], veio {value!r}")
    if not component.get("evidence_ref"):
        raise ScoringError(f"{component_id}: evidence_ref é obrigatório — score sem evidência não é score")
    if not component.get("computed_from"):
        raise ScoringError(f"{component_id}: computed_from é obrigatório")


def _confidence_for(coverage: float) -> str:
    for threshold, label in CONFIDENCE_BY_COVERAGE:
        if coverage >= threshold:
            return label
    return "insufficient"


def score_source(
    source: dict[str, Any],
    components: list[dict[str, Any]],
    *,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Pontua uma fonte a partir dos componentes efetivamente medidos.

    Componentes ausentes são omitidos do cálculo e listados em ``limitations``.
    """
    weights = weights or load_weights()
    if not components:
        raise ScoringError(f"{source.get('source_id')}: nenhum componente medido — sem score possível")

    for component in components:
        _validate_component(component, weights)

    present_ids = [c["component_id"] for c in components]
    if len(set(present_ids)) != len(present_ids):
        raise ScoringError("componente duplicado no mesmo score")

    present_weight = sum(weights[cid] for cid in present_ids)
    weighted = sum(weights[c["component_id"]] * float(c["value"]) for c in components)
    score = weighted / present_weight  # média ponderada SÓ dos presentes

    missing = sorted(set(weights) - set(present_ids))
    limitations = [
        f"componente omitido por ausência de dado: {component_id} (peso {weights[component_id]}) — omitido, não zerado"
        for component_id in missing
    ]
    coverage = len(present_ids) / len(weights)
    if missing:
        limitations.append(
            f"score calculado sobre {len(present_ids)} de {len(weights)} componentes "
            f"({coverage:.0%} do peso declarado) — não comparável a um score completo"
        )
    else:
        limitations.append("todos os componentes declarados foram medidos")

    return {
        "score": round(score, 6),
        "score_components": components,
        "components_present": len(present_ids),
        "components_declared": len(weights),
        "confidence": _confidence_for(coverage),
        "methodology_version": methodology_version(),
        "limitations": limitations,
    }


def build_ranking(
    candidates: list[dict[str, Any]],
    *,
    list_id: str,
    list_scope: str,
    entity_type: str,
    category_id: str,
    target_size: int,
    cut_off_date: str,
) -> dict[str, Any]:
    """Monta uma ranking-list. Nunca preenche, nunca mistura, nunca ranqueia pessoa.

    ``candidates`` são dicts com ``source_id``, ``scored`` (saída de
    :func:`score_source`), ``evidence`` e ``source_ids``.
    """
    if entity_type == "person":
        raise ScoringError(
            "ranqueamento de pessoas é L4: exige DPIA concluída por profissional humano, "
            "base legal mapeada e aprovação de DPO/jurídico (docs/governance/RELEASE_PROTOCOL.md). "
            "O pipeline recusa materializá-lo."
        )
    for candidate in candidates:
        candidate_type = candidate.get("entity_type", entity_type)
        if candidate_type == "person":
            raise ScoringError(f"{candidate.get('source_id')}: entity_type 'person' não pode ser ranqueado")
        if candidate_type != entity_type:
            raise ScoringError(
                f"lista de {entity_type!r} não pode conter {candidate_type!r} — "
                "a Phase C proíbe misturar tipos numa lista só"
            )

    ordered = sorted(candidates, key=lambda item: -item["scored"]["score"])
    today = datetime.now(timezone.utc).date().isoformat()
    version = methodology_version()

    entries = []
    for rank, candidate in enumerate(ordered, start=1):
        scored = candidate["scored"]
        entries.append(
            {
                "entry_id": f"{list_id}-{rank:04d}",
                "list_id": list_id,
                "source_id": candidate["source_id"],
                "rank": rank,
                "score": scored["score"],
                "score_components": scored["score_components"],
                "components_present": scored["components_present"],
                "components_declared": scored["components_declared"],
                "evidence": candidate["evidence"],
                "confidence": scored["confidence"],
                "methodology_version": version,
                "source_ids": candidate["source_ids"],
                "cut_off_date": cut_off_date,
                "validation_date": today,
                "limitations": scored["limitations"],
                "conflicts_of_interest": candidate.get("conflicts_of_interest", []),
                "human_review": {"required": True, "status": "pending"},
            }
        )

    qualified = len(entries)
    coverage_note = (
        f"{qualified} entidades qualificadas de um alvo de {target_size}. "
        "A lista não é preenchida artificialmente: cobertura real é o entregável."
        if qualified < target_size
        else f"{qualified} entidades qualificadas, alvo de {target_size} atingido."
    )

    return {
        "list": {
            "list_id": list_id,
            "list_scope": list_scope,
            "entity_type": entity_type,
            "category_id": category_id,
            "methodology_version": version,
            "cut_off_date": cut_off_date,
            "target_size": target_size,
            "qualified_count": qualified,
            "padded": False,
            "coverage_note": coverage_note,
            "entry_ids": [entry["entry_id"] for entry in entries],
            "human_review": {"required": True, "status": "pending"},
        },
        "entries": entries,
    }
