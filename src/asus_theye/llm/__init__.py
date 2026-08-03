"""Local LLM integration (Ollama) with mandatory audit records."""

from asus_theye.llm.audited import AuditedLocalLLM
from asus_theye.llm.ollama_client import OllamaClient, OllamaError

__all__ = ["AuditedLocalLLM", "OllamaClient", "OllamaError"]
