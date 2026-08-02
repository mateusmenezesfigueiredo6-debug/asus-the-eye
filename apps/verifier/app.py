"""Framework-neutral endpoint facade for a future authenticated verifier Worker/API."""

from __future__ import annotations

from typing import Any

from asus_theye.audit.verifier import verify_document


ROUTES = {
    "GET /event/:id", "GET /proof/:id", "GET /history/:id", "GET /batch/:id",
    "GET /health", "GET /metrics", "POST /verify",
}


def post_verify(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    receipt = verify_document(body)
    return (200 if receipt["status"] != "invalid" else 422), receipt


def health() -> tuple[int, dict[str, str]]:
    return 200, {"status": "ok", "mode": "local", "broadcast": "disabled"}
