# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

path = Path("packages/event-schemas/audit-coverage-manifest.json")
manifest = json.loads(path.read_text(encoding="utf-8"))
required = {"type", "schema", "classification", "retention", "documentation", "handler"}
assert manifest["events"], "coverage manifest is empty"
seen: set[str] = set()
for event in manifest["events"]:
    assert required <= event.keys(), f"coverage fields missing for {event.get('type')}"
    assert event["type"] not in seen, f"duplicate coverage event {event['type']}"
    seen.add(event["type"])
    if event["handler"] == "planned":
        assert {"owner", "reason", "risk", "precondition", "done_when"} <= event.keys()
print(f"PASS: {len(seen)} event families covered")
