# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the schema-validated decision extractor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.decision_context.extractor import (
    DecisionExtractionError,
    extract_decision_fields,
    validate_against_schema,
)
from asus_theye.llm.audited import AuditedLocalLLM


class FakeClient:
    def __init__(self, content: str) -> None:
        self.content = content

    def chat(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> dict:
        return {
            "content": self.content,
            "model": "qwen2.5:3b",
            "duration_ms": 5.0,
            "eval_tokens": 3,
            "prompt_tokens": 9,
        }


def make_llm(tmp_path: Path, content: str) -> AuditedLocalLLM:
    return AuditedLocalLLM(client=FakeClient(content), log_path=tmp_path / "calls.jsonl")


def test_valid_extraction_normalizes_and_tags_fact(tmp_path: Path) -> None:
    model_json = json.dumps(
        {
            "outcome": "granted",
            "decision_form": "collegiate",
            "case_class": "apelacao civel",
            "motion_type": "apelacao",
            "procedural_phase": "recursal",
            "unanimous": True,
        }
    )
    result = extract_decision_fields("texto da decisao", llm=make_llm(tmp_path, model_json))
    assert result["outcome"] == "granted"
    assert result["claim_class"] == "FACT"
    assert result["vote_detail"] == {"unanimous": True}
    assert len(result["extraction_audit_record_hash"]) == 64


def test_unknown_outcome_maps_to_not_known() -> None:
    validated = validate_against_schema({"outcome": "UNKNOWN", "decision_form": "monocratic"})
    assert validated["outcome"] == "not_known"
    assert validated["motion_type"] == "UNKNOWN"


def test_invalid_enum_raises_never_stores() -> None:
    with pytest.raises(DecisionExtractionError, match="decision_form"):
        validate_against_schema({"outcome": "granted", "decision_form": "por_maioria_apertada"})
    with pytest.raises(DecisionExtractionError, match="outcome"):
        validate_against_schema({"outcome": "vai_ganhar", "decision_form": "collegiate"})


def test_non_json_model_output_raises(tmp_path: Path) -> None:
    with pytest.raises(DecisionExtractionError, match="no JSON"):
        extract_decision_fields("texto", llm=make_llm(tmp_path, "o juiz provavelmente concedera"))


def test_empty_text_raises(tmp_path: Path) -> None:
    with pytest.raises(DecisionExtractionError, match="empty"):
        extract_decision_fields("   ", llm=make_llm(tmp_path, "{}"))


def test_extraction_call_is_audited(tmp_path: Path) -> None:
    log = tmp_path / "calls.jsonl"
    llm = AuditedLocalLLM(
        client=FakeClient(json.dumps({"outcome": "denied", "decision_form": "monocratic"})),
        log_path=log,
    )
    extract_decision_fields("texto qualquer", llm=llm)
    assert log.exists()
    record = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert "texto qualquer" not in log.read_text(encoding="utf-8")
    assert len(record["prompt_sha256"]) == 64


def test_lexical_anchor_overrides_model_and_flags(tmp_path: Path) -> None:
    model_json = json.dumps({"outcome": "granted", "decision_form": "monocratic"})
    text = "Acordam os integrantes da Turma, por unanimidade, em dar PARCIAL provimento ao recurso."
    result = extract_decision_fields(text, llm=make_llm(tmp_path, model_json))
    assert result["outcome"] == "partial"
    assert result["decision_form"] == "collegiate"
    assert any(flag.startswith("model_lexical_disagreement:outcome") for flag in result["review_flags"])


def test_no_flags_when_model_agrees_with_anchors(tmp_path: Path) -> None:
    model_json = json.dumps({"outcome": "denied", "decision_form": "monocratic"})
    text = "Decido monocraticamente e nego provimento ao agravo."
    result = extract_decision_fields(text, llm=make_llm(tmp_path, model_json))
    assert result["outcome"] == "denied"
    assert "review_flags" not in result
