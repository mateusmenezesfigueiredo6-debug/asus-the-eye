"""Minimal Ollama chat client. Standard library only, local host only.

The client refuses non-local URLs by default: the whole point of the local
model is that prompts and responses never leave the machine.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = os.environ.get("THE_EYE_LOCAL_MODEL", "qwen2.5:3b")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class OllamaError(RuntimeError):
    """The local model server failed or answered with an error."""


class OllamaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_seconds: int = 300,
        allow_remote: bool = False,
    ) -> None:
        host = urlparse(base_url).hostname
        if not allow_remote and host not in _LOCAL_HOSTS:
            raise OllamaError(f"refusing non-local Ollama host {host!r}; prompts must stay on-machine")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Send one chat turn; returns {content, model, duration_ms, tokens}."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(
                {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                }
            ).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise OllamaError(f"ollama HTTP {error.code}: {detail}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise OllamaError(f"ollama unreachable at {self.base_url} ({error}); is `ollama serve` running?") from error
        if "error" in data:
            raise OllamaError(f"ollama error: {data['error']}")
        return {
            "content": data.get("message", {}).get("content", ""),
            "model": data.get("model", self.model),
            "duration_ms": round(data.get("total_duration", 0) / 1_000_000, 3),
            "eval_tokens": data.get("eval_count"),
            "prompt_tokens": data.get("prompt_eval_count"),
        }
