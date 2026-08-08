"""LLM integration with mandatory audit records.

Local (Ollama) by default; OpenAI and Anthropic are available behind the
``THE_EYE_REMOTE_LLM=1`` gate, and can be paired adversarially via ``dual``.
"""

from asus_theye.llm.audited import AuditedLocalLLM
from asus_theye.llm.dual import CLAIM_CLASSES, DualModelError, adjudicate
from asus_theye.llm.ollama_client import OllamaClient, OllamaError
from asus_theye.llm.remote_client import (
    AnthropicClient,
    OpenAIClient,
    RemoteLLMError,
    build_client,
    remote_enabled,
)

__all__ = [
    "CLAIM_CLASSES",
    "AnthropicClient",
    "AuditedLocalLLM",
    "DualModelError",
    "OllamaClient",
    "OllamaError",
    "OpenAIClient",
    "RemoteLLMError",
    "adjudicate",
    "build_client",
    "remote_enabled",
]
