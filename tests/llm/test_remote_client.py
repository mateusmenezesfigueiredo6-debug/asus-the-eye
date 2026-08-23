# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the remote clients (OpenAI, Anthropic). No network: _post is stubbed."""

from __future__ import annotations

import pytest

from asus_theye.llm import remote_client
from asus_theye.llm.remote_client import (
    ACCEPT_RETENTION_ENV_FLAG,
    ANTHROPIC_COVERED_MODELS,
    DEFAULT_ANTHROPIC_MODEL,
    EXECUTE_ENV_FLAG,
    AnthropicClient,
    OpenAIClient,
    RemoteLLMError,
    build_client,
    normalize_provider,
)


@pytest.fixture
def open_gate(monkeypatch):
    monkeypatch.setenv(EXECUTE_ENV_FLAG, "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")


class TestNormalizeProvider:
    @pytest.mark.parametrize(
        ("alias", "canonical"),
        [
            ("openai", "openai"),
            ("chatgpt", "openai"),
            ("ChatGPT", "openai"),
            ("gpt", "openai"),
            ("anthropic", "anthropic"),
            ("claude", "anthropic"),
            ("Claude", "anthropic"),
            ("local", "local"),
            ("ollama", "local"),
        ],
    )
    def test_aliases_collapse_to_canonical_names(self, alias, canonical):
        assert normalize_provider(alias) == canonical

    def test_unknown_provider_is_rejected(self):
        with pytest.raises(RemoteLLMError, match="unknown provider"):
            normalize_provider("gemini")


class TestOpenAIClient:
    def test_chat_parses_choices_and_usage(self, open_gate, monkeypatch):
        captured = {}

        def fake_post(url, payload, headers, timeout):
            captured.update(url=url, payload=payload, headers=headers)
            return {
                "model": "gpt-4o-2024",
                "choices": [{"message": {"role": "assistant", "content": "ola"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            }

        monkeypatch.setattr(remote_client, "_post", fake_post)
        result = OpenAIClient().chat("pergunta", system="regras")

        assert result["content"] == "ola"
        assert result["model"] == "gpt-4o-2024"
        assert result["prompt_tokens"] == 7
        assert result["eval_tokens"] == 3
        assert captured["payload"]["messages"][0] == {"role": "system", "content": "regras"}
        assert captured["payload"]["messages"][1] == {"role": "user", "content": "pergunta"}
        assert captured["headers"]["authorization"] == "Bearer test-openai-key"

    def test_empty_choices_yield_empty_content(self, open_gate, monkeypatch):
        monkeypatch.setattr(remote_client, "_post", lambda *a: {"choices": []})
        assert OpenAIClient().chat("pergunta")["content"] == ""


class TestAnthropicClient:
    def test_chat_joins_text_blocks_and_maps_usage(self, open_gate, monkeypatch):
        captured = {}

        def fake_post(url, payload, headers, timeout):
            captured.update(url=url, payload=payload, headers=headers)
            return {
                "model": "claude-opus-5",
                "content": [
                    {"type": "text", "text": "parte um. "},
                    {"type": "thinking", "thinking": "nunca vaza"},
                    {"type": "text", "text": "parte dois."},
                ],
                "usage": {"input_tokens": 11, "output_tokens": 5},
            }

        monkeypatch.setattr(remote_client, "_post", fake_post)
        result = AnthropicClient().chat("pergunta", system="regras")

        assert result["content"] == "parte um. parte dois."
        assert result["prompt_tokens"] == 11
        assert result["eval_tokens"] == 5
        assert captured["payload"]["system"] == "regras"
        assert captured["payload"]["max_tokens"] > 0
        assert captured["headers"]["x-api-key"] == "test-anthropic-key"
        assert "anthropic-version" in captured["headers"]

    def test_system_absent_when_not_given(self, open_gate, monkeypatch):
        captured = {}

        def fake_post(url, payload, headers, timeout):
            captured["payload"] = payload
            return {"content": [], "usage": {}}

        monkeypatch.setattr(remote_client, "_post", fake_post)
        AnthropicClient().chat("pergunta")
        assert "system" not in captured["payload"]


class TestBuildClientAliases:
    def test_chatgpt_builds_the_openai_client(self, open_gate):
        client = build_client("chatgpt")
        assert isinstance(client, OpenAIClient)
        assert client.provider == "openai"

    def test_claude_builds_the_anthropic_client(self, open_gate):
        client = build_client("claude")
        assert isinstance(client, AnthropicClient)
        assert client.provider == "anthropic"

    def test_aliases_do_not_bypass_the_gate(self, monkeypatch):
        monkeypatch.delenv(EXECUTE_ENV_FLAG, raising=False)
        for alias in ("chatgpt", "claude"):
            with pytest.raises(RemoteLLMError, match="gated"):
                build_client(alias)


class TestRetencaoCoveredModel:
    """Um Covered Model obriga 30 dias de retencao; isso nao pode ser padrao."""

    def test_covered_model_e_recusado_sem_consentimento(self, open_gate, monkeypatch):
        monkeypatch.delenv(ACCEPT_RETENTION_ENV_FLAG, raising=False)
        for modelo in ("claude-fable-5", "claude-mythos-5"):
            with pytest.raises(RemoteLLMError, match="Covered Model"):
                AnthropicClient(model=modelo)

    def test_consentimento_explicito_libera(self, open_gate, monkeypatch):
        monkeypatch.setenv(ACCEPT_RETENTION_ENV_FLAG, "1")
        assert AnthropicClient(model="claude-fable-5").model == "claude-fable-5"

    def test_o_padrao_do_projeto_nao_e_covered(self, open_gate, monkeypatch):
        """claude-opus-5 preserva a opcao de retencao zero — nao pode regredir."""
        monkeypatch.delenv(ACCEPT_RETENTION_ENV_FLAG, raising=False)
        assert DEFAULT_ANTHROPIC_MODEL not in ANTHROPIC_COVERED_MODELS
        assert AnthropicClient().model == DEFAULT_ANTHROPIC_MODEL

    def test_a_recusa_vem_antes_da_chave(self, open_gate, monkeypatch):
        """Sem chave E com modelo coberto, o erro que importa e o da retencao."""
        monkeypatch.delenv(ACCEPT_RETENTION_ENV_FLAG, raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RemoteLLMError, match="Covered Model"):
            AnthropicClient(model="claude-fable-5")

    def test_a_porta_ainda_vem_antes_de_tudo(self, monkeypatch):
        monkeypatch.delenv(EXECUTE_ENV_FLAG, raising=False)
        monkeypatch.setenv(ACCEPT_RETENTION_ENV_FLAG, "1")
        with pytest.raises(RemoteLLMError, match="gated"):
            AnthropicClient(model="claude-fable-5")
