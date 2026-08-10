"""Remote LLM clients (OpenAI, Anthropic) behind an explicit execution gate.

The local Ollama path guarantees that prompts never leave the machine. These
clients deliberately break that guarantee, so they are gated the same way the
IBM QPU path is gated (see ``ibm_backend``): nothing reaches a third party
unless ``THE_EYE_REMOTE_LLM=1`` is set *and* the caller asked for a remote
provider by name. There is no implicit fallback from local to remote — a
missing gate raises, it does not silently downgrade the privacy posture.

Never send Phase G decision-context payloads through here: those carry
LGPD-relevant judicial data and are local-only by construction (ADR-001).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

EXECUTE_ENV_FLAG = "THE_EYE_REMOTE_LLM"

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

DEFAULT_OPENAI_MODEL = os.environ.get("THE_EYE_OPENAI_MODEL", "gpt-4o")
DEFAULT_ANTHROPIC_MODEL = os.environ.get("THE_EYE_ANTHROPIC_MODEL", "claude-opus-5")

# The owner says "chatGPT" and "Claude"; the audit trail says "openai" and
# "anthropic". Both vocabularies resolve to the same canonical provider so the
# hash chain never records two names for one origin.
PROVIDER_ALIASES = {
    "local": "local",
    "ollama": "local",
    "openai": "openai",
    "chatgpt": "openai",
    "gpt": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
}


def normalize_provider(provider: str) -> str:
    """Map a provider name or alias onto local, openai, or anthropic."""
    normalized = PROVIDER_ALIASES.get(provider.strip().lower())
    if normalized is None:
        raise RemoteLLMError(f"unknown provider {provider!r}; expected one of {sorted(set(PROVIDER_ALIASES))}")
    return normalized


class RemoteLLMError(RuntimeError):
    """A remote provider was unreachable, refused the call, or is not gated."""


def remote_enabled() -> bool:
    """True only when the operator explicitly opened the remote gate."""
    return os.environ.get(EXECUTE_ENV_FLAG) == "1"


def _require_gate(provider: str) -> None:
    if not remote_enabled():
        raise RemoteLLMError(
            f"remote provider {provider!r} is gated: prompts would leave this machine. "
            f"Set {EXECUTE_ENV_FLAG}=1 to allow it, and never for Phase G judicial data."
        )


def _post(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RemoteLLMError(f"HTTP {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RemoteLLMError(f"{url} unreachable ({error})") from error


class OpenAIClient:
    """Chat client for OpenAI, matching the ``OllamaClient.chat`` contract."""

    provider = "openai"

    def __init__(
        self,
        model: str = DEFAULT_OPENAI_MODEL,
        api_key: str | None = None,
        timeout_seconds: int = 300,
    ) -> None:
        _require_gate(self.provider)
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RemoteLLMError("OPENAI_API_KEY is not set")
        self.timeout_seconds = timeout_seconds

    def chat(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        started = time.monotonic()
        data = _post(
            OPENAI_URL,
            {"model": self.model, "messages": messages, "temperature": temperature},
            {"authorization": f"Bearer {self.api_key}"},
            self.timeout_seconds,
        )
        elapsed_ms = round((time.monotonic() - started) * 1000, 3)

        choices = data.get("choices") or []
        usage = data.get("usage") or {}
        return {
            "content": choices[0].get("message", {}).get("content", "") if choices else "",
            "model": data.get("model", self.model),
            "duration_ms": elapsed_ms,
            "prompt_tokens": usage.get("prompt_tokens"),
            "eval_tokens": usage.get("completion_tokens"),
        }


class AnthropicClient:
    """Chat client for Anthropic, matching the ``OllamaClient.chat`` contract."""

    provider = "anthropic"

    def __init__(
        self,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        api_key: str | None = None,
        timeout_seconds: int = 300,
        max_tokens: int = 4096,
    ) -> None:
        _require_gate(self.provider)
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise RemoteLLMError("ANTHROPIC_API_KEY is not set")
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    def chat(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        started = time.monotonic()
        data = _post(
            ANTHROPIC_URL,
            payload,
            {"x-api-key": self.api_key, "anthropic-version": ANTHROPIC_VERSION},
            self.timeout_seconds,
        )
        elapsed_ms = round((time.monotonic() - started) * 1000, 3)

        blocks = data.get("content") or []
        text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        usage = data.get("usage") or {}
        return {
            "content": text,
            "model": data.get("model", self.model),
            "duration_ms": elapsed_ms,
            "prompt_tokens": usage.get("input_tokens"),
            "eval_tokens": usage.get("output_tokens"),
        }


def build_client(provider: str, model: str | None = None) -> Any:
    """Return a chat client for ``provider``: local, openai, or anthropic.

    Accepts the aliases in ``PROVIDER_ALIASES`` (chatgpt, gpt, claude, ollama).
    """
    normalized = normalize_provider(provider)
    if normalized == "local":
        from asus_theye.llm.ollama_client import OllamaClient

        return OllamaClient(model=model) if model else OllamaClient()
    if normalized == "openai":
        return OpenAIClient(model=model or DEFAULT_OPENAI_MODEL)
    return AnthropicClient(model=model or DEFAULT_ANTHROPIC_MODEL)
