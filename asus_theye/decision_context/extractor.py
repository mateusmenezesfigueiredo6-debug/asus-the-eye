"""Extract procedural facts from public decision text using the local LLM.

Policy encoding (Phase G / AGENTS.md):

- the model extracts procedural facts only (outcome, form, class, phase);
- any field the text does not clearly state becomes ``"UNKNOWN"`` — the prompt
  and the validator both enforce this;
- extraction runs on the *local* model (prompts never leave the machine), and
  every call is hash-chain audited via :class:`AuditedLocalLLM`;
- the result is validated against ``public-decisions.schema.json`` enums before
  anyone may store it. Validation failure raises; it never degrades silently.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from asus_theye.llm.audited import AuditedLocalLLM

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "decision-context" / "public-decisions.schema.json"
)

SYSTEM_PROMPT = """Voce extrai FATOS PROCESSUAIS de decisoes judiciais publicas.

Responda APENAS um objeto JSON com estas chaves:
- "outcome": um de ["granted","denied","partial","not_known","converted","prejudicado"]
- "decision_form": um de ["monocratic","collegiate"]
- "case_class": classe processual citada no texto, ou "UNKNOWN"
- "motion_type": tipo de pedido/recurso decidido, ou "UNKNOWN"
- "procedural_phase": fase processual, ou "UNKNOWN"
- "unanimous": true, false ou null se o texto nao disser

MAPEAMENTO DE VOCABULARIO (siga exatamente):
- "dar provimento" / "julgo procedente" / "concedo" -> outcome "granted"
- "PARCIAL provimento" / "parcialmente procedente" -> outcome "partial"
- "negar provimento" / "julgo improcedente" / "indefiro" -> outcome "denied"
- "prejudicado" -> outcome "prejudicado"
- "acordam" / "Turma" / "Camara" / "sessao colegiada" / "votos" -> decision_form "collegiate"
- "decido monocraticamente" / "decisao do relator" sem colegiado -> decision_form "monocratic"
- "por unanimidade" -> unanimous true; "por maioria" -> unanimous false

REGRAS OBRIGATORIAS:
1. Use somente o que o texto afirma explicitamente. Nada de inferencia.
2. Campo nao afirmado claramente = "UNKNOWN" (ou null para "unanimous").
3. Se o texto diz "PARCIAL", o outcome e "partial", nunca "granted".
4. NUNCA opine sobre o julgador, ideologia, ou como alguem decidira no futuro.
5. Nenhum texto fora do JSON."""

_ALLOWED_UNKNOWN = "UNKNOWN"

# High-precision lexical anchors. When one of these matches, it overrides the
# model: small local models misread critical Portuguese legal formulas (e.g.
# "PARCIAL provimento" classified as granted), and a wrong outcome may never be
# stored as FACT. Order matters: partial before granted.
_OUTCOME_ANCHORS: tuple[tuple[str, str], ...] = (
    (r"parcial(?:mente)?\s+prov|prov[a-z]*\s+parcial|parcialmente\s+procedente", "partial"),
    (r"negar?\s+provimento|nega-se\s+provimento|nego\s+provimento|julgo\s+improcedente|improcedente", "denied"),
    (r"dar\s+provimento|da-se\s+provimento|dou\s+provimento|julgo\s+procedente", "granted"),
    (r"prejudicad[oa]", "prejudicado"),
)
_FORM_ANCHORS: tuple[tuple[str, str], ...] = (
    (r"acordam|turma\s+julgadora|sess[aã]o\s+colegiada|c[aâ]mara|colegiad[oa]", "collegiate"),
    (r"decido\s+monocraticamente|decis[aã]o\s+monocr[aá]tica", "monocratic"),
)


def _lexical_match(text: str, anchors: tuple[tuple[str, str], ...]) -> str | None:
    lowered = text.lower()
    for pattern, value in anchors:
        if re.search(pattern, lowered):
            return value
    return None


class DecisionExtractionError(RuntimeError):
    """The model output could not be validated against the schema."""


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _extract_json(raw: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise DecisionExtractionError(f"model returned no JSON object: {raw[:200]!r}")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as error:
        raise DecisionExtractionError(f"model returned invalid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise DecisionExtractionError("model JSON is not an object")
    return parsed


def validate_against_schema(candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate extracted fields against public-decisions enums.

    Returns a normalized copy. Raises :class:`DecisionExtractionError` on any
    value outside the schema — invalid extractions must never be stored.
    """
    schema_properties = _load_schema()["properties"]
    outcome_enum = set(schema_properties["outcome"]["enum"])
    form_enum = set(schema_properties["decision_form"]["enum"])

    outcome = candidate.get("outcome", _ALLOWED_UNKNOWN)
    if outcome == _ALLOWED_UNKNOWN:
        outcome = "not_known"
    if outcome not in outcome_enum:
        raise DecisionExtractionError(f"outcome {outcome!r} not in schema enum {sorted(outcome_enum)}")

    decision_form = candidate.get("decision_form")
    if decision_form not in form_enum:
        raise DecisionExtractionError(
            f"decision_form {decision_form!r} not in schema enum {sorted(form_enum)}"
        )

    normalized = {
        "outcome": outcome,
        "decision_form": decision_form,
        "case_class": str(candidate.get("case_class") or _ALLOWED_UNKNOWN),
        "motion_type": str(candidate.get("motion_type") or _ALLOWED_UNKNOWN),
        "procedural_phase": str(candidate.get("procedural_phase") or _ALLOWED_UNKNOWN),
        "claim_class": "FACT",
    }
    unanimous = candidate.get("unanimous")
    if isinstance(unanimous, bool):
        normalized["vote_detail"] = {"unanimous": unanimous}
    return normalized


def extract_decision_fields(
    decision_text: str,
    llm: AuditedLocalLLM | None = None,
) -> dict[str, Any]:
    """Run the audited local extraction and return schema-validated fields."""
    if not decision_text.strip():
        raise DecisionExtractionError("decision text is empty")
    llm = llm or AuditedLocalLLM()
    outcome = llm.chat(decision_text, system=SYSTEM_PROMPT, temperature=0.0)
    validated = validate_against_schema(_extract_json(outcome["content"]))

    # Hybrid reconciliation: deterministic anchors override the model, and any
    # disagreement is flagged for the mandatory human review instead of being
    # silently accepted from either side.
    review_flags: list[str] = []
    for field, anchors in (("outcome", _OUTCOME_ANCHORS), ("decision_form", _FORM_ANCHORS)):
        anchored = _lexical_match(decision_text, anchors)
        if anchored is not None and anchored != validated[field]:
            review_flags.append(f"model_lexical_disagreement:{field}:model={validated[field]}")
            validated[field] = anchored
    if review_flags:
        validated["review_flags"] = review_flags

    validated["extraction_audit_record_hash"] = outcome["audit_record"]["record_hash_sha256"]
    return validated
