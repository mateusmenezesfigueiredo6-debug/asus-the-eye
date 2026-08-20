# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Local Queue-consumer reference; contains no Cloudflare credentials or deployment calls."""

from __future__ import annotations

from typing import Any

from asus_theye.audit.schema import verify_event
from asus_theye.audit.sdk import SQLiteAuditStore


def consume(messages: list[dict[str, Any]], store: SQLiteAuditStore) -> dict[str, int]:
    """Model at-least-once delivery: duplicates are acknowledged, failures go to DLQ."""
    result = {"accepted": 0, "duplicates": 0, "dead_letter": 0}
    for event in messages:
        if not verify_event(event):
            result["dead_letter"] += 1
            continue
        try:
            receipt = store.append(event)
        except (ValueError, TypeError):
            result["dead_letter"] += 1
        else:
            result["duplicates" if receipt["duplicate"] else "accepted"] += 1
    return result
