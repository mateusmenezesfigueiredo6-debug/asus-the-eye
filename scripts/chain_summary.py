#!/usr/bin/env python3
"""Resumo de uma linha da cadeia de eventos. Lê o JSON do ledger em stdin."""

from __future__ import annotations

import json
import sys

GREEN, RESET = "\033[0;32m", "\033[0m"


def main() -> int:
    try:
        events = json.load(sys.stdin).get("events", [])
    except ValueError:
        print("    resposta ilegível do ledger")
        return 0
    if not events:
        print("    cadeia vazia")
        return 0
    top = max(event["sequence"] for event in events)
    print(f"  {GREEN}✓{RESET} {len(events)} eventos encadeados (topo: sequência {top})")
    for event in sorted(events, key=lambda item: -item["sequence"])[:3]:
        print(f"    seq {event['sequence']}: {event['event_type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
