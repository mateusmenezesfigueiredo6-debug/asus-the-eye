# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Minimal hash-chained JSONL ledger for benchmark evidence."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64


def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class AuditLedger:
    """Append metric events while protecting ordering and content with SHA-256."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        previous_hash = GENESIS_HASH
        sequence = 1
        if self.path.exists() and self.path.stat().st_size:
            with self.path.open("rb") as stream:
                last_line = list(stream)[-1]
            previous = json.loads(last_line)
            previous_hash = previous["hash"]
            sequence = int(previous["sequence"]) + 1
        body = {
            "sequence": sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        record = {**body, "hash": hashlib.sha256(_canonical(body).encode()).hexdigest()}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(_canonical(record) + "\n")
            stream.flush()
            # flush() só empurra do buffer do Python para o sistema operacional.
            # Sem fsync, um desligamento entre as duas coisas deixa o arquivo
            # ESTENDIDO mas com o conteúdo por gravar — e o ext4 preenche o
            # buraco com zeros. Foi exatamente o que aconteceu em 30/08: a
            # corrente ganhou uma cauda de 2.413 bytes nulos depois do elo 68 e
            # a verificação passou a falhar com JSONDecodeError. Nenhum elo se
            # perdeu, mas a prova de custódia ficou ilegível até o reparo.
            os.fsync(stream.fileno())
        return record


def verify_ledger(path: str | Path) -> bool:
    ledger_path = Path(path)
    previous_hash = GENESIS_HASH
    if not ledger_path.exists():
        return True
    with ledger_path.open(encoding="utf-8") as stream:
        for sequence, line in enumerate(stream, start=1):
            record = json.loads(line)
            body = {key: value for key, value in record.items() if key != "hash"}
            expected = hashlib.sha256(_canonical(body).encode()).hexdigest()
            if (
                record.get("sequence") != sequence
                or record.get("previous_hash") != previous_hash
                or record.get("hash") != expected
            ):
                return False
            previous_hash = record["hash"]
    return True
