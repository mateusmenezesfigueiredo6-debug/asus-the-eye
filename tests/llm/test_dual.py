"""Tests for the two-model adjudication. No network: clients are stubs."""

from __future__ import annotations

import json
from typing import Any

import pytest

from asus_theye.llm import dual
from asus_theye.llm.dual import DualModelError, adjudicate
from asus_theye.llm.remote_client import EXECUTE_ENV_FLAG, RemoteLLMError, build_client, remote_enabled


class StubClient:
    """Returns a canned payload and records what it was asked."""

    def __init__(self, provider: str, payload: dict[str, Any] | str, model: str = "stub-1") -> None:
        self.provider = provider
        self.payload = payload
        self.model = model
        self.calls: list[dict[str, Any]] = []

    def chat(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> dict[str, Any]:
        self.calls.append({"prompt": prompt, "system": system, "temperature": temperature})
        content = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return {
            "content": content,
            "model": self.model,
            "duration_ms": 1.0,
            "prompt_tokens": 10,
            "eval_tokens": 20,
        }


PROPOSAL = {
    "claim": "A cadeia de auditoria usa SHA-256 encadeado.",
    "claim_class": "FACT",
    "primary_evidence": ["audited.py encadeia previous_record_hash_sha256"],
    "justification": "O código escreve o hash do registro anterior em cada linha.",
    "confidence": 0.9,
    "limitations": ["Vale só para o log local."],
    "what_would_change_it": "Trocar o algoritmo de hash.",
}

AGREEING_CHALLENGE = {
    "agrees_with_claim": True,
    "contrary_evidence": ["Nenhuma evidência contrária encontrada no código."],
    "claim_class": "FACT",
    "confidence": 0.8,
    "divergences": [],
    "critique": "A alegação se sustenta.",
}

REFUTING_CHALLENGE = {
    "agrees_with_claim": False,
    "contrary_evidence": ["O encadeamento não é verificado na leitura."],
    "claim_class": "INFERENCE",
    "confidence": 0.4,
    "divergences": ["Ninguém valida a cadeia ao ler."],
    "critique": "Escrever o hash não prova que a cadeia é verificada.",
}


@pytest.fixture(autouse=True)
def _isolate_audit_log(tmp_path, monkeypatch):
    """Keep the hash-chained audit log out of the real reports/ directory."""
    monkeypatch.setattr(dual.AuditedLocalLLM, "log_path", tmp_path / "calls.jsonl", raising=False)
    monkeypatch.chdir(tmp_path)


def _patch_clients(monkeypatch, proposer: StubClient, challenger: StubClient) -> None:
    clients = iter([proposer, challenger])
    monkeypatch.setattr(dual, "build_client", lambda provider, model=None: next(clients))


def test_agreement_keeps_the_claim_class(monkeypatch):
    _patch_clients(
        monkeypatch,
        StubClient("openai", PROPOSAL),
        StubClient("anthropic", AGREEING_CHALLENGE),
    )
    verdict = adjudicate("A cadeia é encadeada?")

    assert verdict["claim_class"] == "FACT"
    assert verdict["agreement"] is True
    assert verdict["contrary_evidence"]
    assert verdict["proposer"]["provider"] == "openai"
    assert verdict["challenger"]["provider"] == "anthropic"


def test_disagreement_downgrades_to_conflicted(monkeypatch):
    _patch_clients(
        monkeypatch,
        StubClient("openai", PROPOSAL),
        StubClient("anthropic", REFUTING_CHALLENGE),
    )
    verdict = adjudicate("A cadeia é encadeada?")

    assert verdict["claim_class"] == "CONFLICTED"
    assert verdict["agreement"] is False
    assert any("FACT" in item and "INFERENCE" in item for item in verdict["divergences"])


def test_challenger_can_only_lower_confidence(monkeypatch):
    overconfident = dict(AGREEING_CHALLENGE, confidence=1.0)
    _patch_clients(
        monkeypatch,
        StubClient("openai", dict(PROPOSAL, confidence=0.5)),
        StubClient("anthropic", overconfident),
    )
    verdict = adjudicate("A cadeia é encadeada?")

    assert verdict["confidence"] == 0.5


def test_same_class_but_disagreement_still_conflicts(monkeypatch):
    """Agreeing on the label while rejecting the substance is not agreement."""
    _patch_clients(
        monkeypatch,
        StubClient("openai", PROPOSAL),
        StubClient("anthropic", dict(REFUTING_CHALLENGE, claim_class="FACT")),
    )
    verdict = adjudicate("A cadeia é encadeada?")

    assert verdict["claim_class"] == "CONFLICTED"


def test_challenger_receives_the_claim_to_attack(monkeypatch):
    challenger = StubClient("anthropic", AGREEING_CHALLENGE)
    _patch_clients(monkeypatch, StubClient("openai", PROPOSAL), challenger)
    adjudicate("A cadeia é encadeada?")

    sent = challenger.calls[0]["prompt"]
    assert PROPOSAL["claim"] in sent
    assert "FACT" in sent
    assert "adversary" in (challenger.calls[0]["system"] or "").lower()


def test_json_inside_code_fences_is_parsed(monkeypatch):
    fenced = f"Here you go:\n```json\n{json.dumps(PROPOSAL)}\n```\nDone."
    _patch_clients(
        monkeypatch,
        StubClient("openai", fenced),
        StubClient("anthropic", AGREEING_CHALLENGE),
    )
    verdict = adjudicate("A cadeia é encadeada?")

    assert verdict["claim"] == PROPOSAL["claim"]


def test_unparseable_output_raises(monkeypatch):
    _patch_clients(
        monkeypatch,
        StubClient("openai", "desculpa, não consigo responder"),
        StubClient("anthropic", AGREEING_CHALLENGE),
    )
    with pytest.raises(DualModelError, match="did not return JSON"):
        adjudicate("A cadeia é encadeada?")


def test_unknown_claim_class_falls_back_to_unknown(monkeypatch):
    _patch_clients(
        monkeypatch,
        StubClient("openai", dict(PROPOSAL, claim_class="TOTALMENTE_CERTO")),
        StubClient("anthropic", dict(AGREEING_CHALLENGE, claim_class="TOTALMENTE_CERTO")),
    )
    verdict = adjudicate("A cadeia é encadeada?")

    assert verdict["claim_class"] == "UNKNOWN"


def test_a_model_cannot_review_itself():
    with pytest.raises(DualModelError, match="cannot adversarially"):
        adjudicate("qualquer", proposer="openai", challenger="openai")


def test_an_alias_cannot_dodge_the_self_review_guard():
    """"chatgpt" and "openai" are one provider; the guard sees through the alias."""
    with pytest.raises(DualModelError, match="cannot adversarially"):
        adjudicate("qualquer", proposer="chatgpt", challenger="openai")


def test_aliases_are_recorded_under_their_canonical_names(monkeypatch):
    _patch_clients(
        monkeypatch,
        StubClient("openai", PROPOSAL),
        StubClient("anthropic", AGREEING_CHALLENGE),
    )
    verdict = adjudicate("A cadeia é encadeada?", proposer="chatgpt", challenger="claude")

    assert verdict["proposer"]["provider"] == "openai"
    assert verdict["challenger"]["provider"] == "anthropic"


def test_empty_claim_is_rejected(monkeypatch):
    _patch_clients(
        monkeypatch,
        StubClient("openai", dict(PROPOSAL, claim="   ")),
        StubClient("anthropic", AGREEING_CHALLENGE),
    )
    with pytest.raises(DualModelError, match="empty claim"):
        adjudicate("A cadeia é encadeada?")


def test_audit_record_reports_the_real_backend(monkeypatch):
    _patch_clients(
        monkeypatch,
        StubClient("openai", PROPOSAL, model="gpt-stub"),
        StubClient("anthropic", AGREEING_CHALLENGE, model="claude-stub"),
    )
    verdict = adjudicate("A cadeia é encadeada?")

    assert verdict["proposer"]["model"] == "gpt-stub"
    assert verdict["challenger"]["model"] == "claude-stub"
    assert verdict["proposer"]["record_hash_sha256"] != verdict["challenger"]["record_hash_sha256"]


class TestRemoteGate:
    def test_gate_is_closed_by_default(self, monkeypatch):
        monkeypatch.delenv(EXECUTE_ENV_FLAG, raising=False)
        assert remote_enabled() is False
        with pytest.raises(RemoteLLMError, match="gated"):
            build_client("openai")

    def test_open_gate_still_requires_a_key(self, monkeypatch):
        monkeypatch.setenv(EXECUTE_ENV_FLAG, "1")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RemoteLLMError, match="ANTHROPIC_API_KEY"):
            build_client("anthropic")

    def test_local_provider_needs_no_gate(self, monkeypatch):
        monkeypatch.delenv(EXECUTE_ENV_FLAG, raising=False)
        client = build_client("local")
        assert client.base_url.startswith("http://localhost")

    def test_unknown_provider_is_rejected(self, monkeypatch):
        monkeypatch.setenv(EXECUTE_ENV_FLAG, "1")
        with pytest.raises(RemoteLLMError, match="unknown provider"):
            build_client("gemini")
