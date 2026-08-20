# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the audited local LLM wrapper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.llm.audited import GENESIS_HASH, AuditedLocalLLM
from asus_theye.llm.ollama_client import OllamaClient, OllamaError


class FakeClient:
    def __init__(self, content: str = "resposta local") -> None:
        self.content = content
        self.calls: list[dict] = []

    def chat(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> dict:
        self.calls.append({"prompt": prompt, "system": system})
        return {
            "content": self.content,
            "model": "qwen2.5:3b",
            "duration_ms": 12.5,
            "eval_tokens": 7,
            "prompt_tokens": 11,
        }


def test_refuses_remote_host() -> None:
    with pytest.raises(OllamaError, match="non-local"):
        OllamaClient(base_url="http://evil.example:11434")


def test_chat_writes_hash_chained_local_records(tmp_path: Path) -> None:
    log = tmp_path / "calls.jsonl"
    llm = AuditedLocalLLM(client=FakeClient(), log_path=log)

    first = llm.chat("primeiro prompt")["audit_record"]
    second = llm.chat("segundo prompt")["audit_record"]

    assert first["previous_record_hash_sha256"] == GENESIS_HASH
    assert second["previous_record_hash_sha256"] == first["record_hash_sha256"]
    lines = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert lines[1]["record_hash_sha256"] == second["record_hash_sha256"]


def test_raw_text_never_reaches_remote_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[dict] = []

    def fake_publish(body: dict, ledger_url: str) -> dict:
        published.append(body)
        return {"sequence": 9, "event_hash_sha256": "cd" * 32}

    monkeypatch.setattr("asus_theye.llm.audited.publish_event", fake_publish)
    llm = AuditedLocalLLM(
        client=FakeClient(content="conteudo secreto local"),
        log_path=tmp_path / "calls.jsonl",
        ledger_url="https://ledger.example",
    )
    outcome = llm.chat("um prompt bem privado")

    assert outcome["ledger_receipt"]["sequence"] == 9
    serialized = json.dumps(published)
    assert "um prompt bem privado" not in serialized
    assert "conteudo secreto local" not in serialized
    assert published[0]["payload"]["prompt_sha256"] == outcome["audit_record"]["prompt_sha256"]


def test_local_record_contains_hashes_not_text(tmp_path: Path) -> None:
    log = tmp_path / "calls.jsonl"
    llm = AuditedLocalLLM(client=FakeClient(content="texto da resposta"), log_path=log)
    llm.chat("prompt confidencial")
    raw = log.read_text(encoding="utf-8")
    assert "prompt confidencial" not in raw
    assert "texto da resposta" not in raw
