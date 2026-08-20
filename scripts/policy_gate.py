# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import re
from pathlib import Path

root = Path(".")
env_files = [p for p in root.rglob(".env") if ".git" not in p.parts and "chaves" not in p.parts]
assert not env_files, f"real .env files forbidden: {env_files}"
example = Path("contracts/audit-anchor/.env.example").read_text()
assert "BLOCKCHAIN_BROADCAST_ENABLED=false" in example
assert "BLOCKCHAIN_NETWORK=local" in example
assert not re.search(r"PRIVATE_KEY\s*=", example, re.I)
contract = Path("contracts/audit-anchor/src/TheEyeAuditAnchor.sol").read_text()
anchor_start = contract.index("function anchorBatch")
signature = contract[anchor_start : contract.index(") external", anchor_start)]
assert "string" not in signature and "bytes " not in signature, "anchor accepts arbitrary content"
assert "bytes32 manifestHash" in signature and "onlyRole(ANCHOR_ROLE)" in contract
for path in root.rglob("*"):
    # publish_guard.py and this file name the forbidden command in order to block
    # it; matching on the mention would flag the very tooling that prevents it.
    SELF_REFERENTIAL = {"policy_gate.py", "publish_guard.py"}
    if not path.is_file() or ".git" in path.parts or "chaves" in path.parts or path.name in SELF_REFERENTIAL:
        continue
    if path.suffix in {".py", ".toml", ".yml", ".yaml", ".sol", ".ts"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "forge --broadcast" not in text, f"broadcast command in {path}"
print("PASS: broadcast-off, no real env/private key, narrow anchor ABI")
