# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the remote ledger publisher."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from asus_theye.audit.remote_ledger import (
    LedgerPublishError,
    build_benchmark_event,
    publish_benchmark_report,
)

SAMPLE_REPORT = {
    "project": "ASUS THE EYE",
    "engine_version": "0.2.0",
    "date": "2026-08-02T08:21:39+00:00",
    "problem": {"name": "demo_portfolio_v1"},
    "results": {
        "classical": {"score": 28.0},
        "qubo": {"score": 28.0},
        "qaoa": {"score": 28.0, "backend": "local_simulator", "hardware_execution": False},
    },
    "metrics": {"qar": {"qar": 1.0}},
}


def test_build_event_is_deterministic() -> None:
    first = build_benchmark_event(SAMPLE_REPORT)
    second = build_benchmark_event(json.loads(json.dumps(SAMPLE_REPORT)))
    assert first == second
    assert first["idempotency_key"].startswith("benchmark-")
    assert first["event_type"] == "benchmark.completed"


def test_build_event_changes_with_report_content() -> None:
    modified = json.loads(json.dumps(SAMPLE_REPORT))
    modified["metrics"]["qar"]["qar"] = 1.1
    assert (
        build_benchmark_event(SAMPLE_REPORT)["idempotency_key"] != (build_benchmark_event(modified)["idempotency_key"])
    )


def test_build_event_publishes_summary_not_full_report() -> None:
    payload = build_benchmark_event(SAMPLE_REPORT)["payload"]
    assert payload["qar"] == 1.0
    assert payload["hardware_execution"] is False
    assert len(payload["report_hash_sha256"]) == 64
    # The full report (solutions, angles, problem data) must stay local.
    assert "results" not in payload
    assert "solution" not in json.dumps(payload)


def test_publish_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse(io.BytesIO):
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            self.close()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(json.dumps({"sequence": 4, "event_hash_sha256": "ab" * 32}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    receipt = publish_benchmark_report(SAMPLE_REPORT, "https://ledger.example/")
    assert receipt["sequence"] == 4
    assert captured["url"] == "https://ledger.example/events"
    assert captured["body"]["tenant_id"] == "tenant-demo"


def test_publish_fails_loudly_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url, 422, "Unprocessable", {}, io.BytesIO(b'{"error":"missing field"}')
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(LedgerPublishError, match="HTTP 422"):
        publish_benchmark_report(SAMPLE_REPORT, "https://ledger.example")


def test_publish_fails_loudly_when_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(LedgerPublishError, match="unreachable"):
        publish_benchmark_report(SAMPLE_REPORT, "https://ledger.example")
