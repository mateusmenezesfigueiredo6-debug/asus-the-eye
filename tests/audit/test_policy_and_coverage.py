from __future__ import annotations

import json
import runpy
from pathlib import Path


def test_event_coverage_gate():
    runpy.run_path("scripts/event_coverage.py")


def test_policy_gate():
    runpy.run_path("scripts/policy_gate.py")


def test_schema_has_every_required_privacy_field():
    schema = json.loads(Path("packages/event-schemas/audit-event.schema.json").read_text())
    assert "event_hash_sha256" in schema["required"]
    assert schema["additionalProperties"] is False
    assert not {"name", "email", "cpf", "document_content", "prompt", "response"} & set(schema["properties"])
