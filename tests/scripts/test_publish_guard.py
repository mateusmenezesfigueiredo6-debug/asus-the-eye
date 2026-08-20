# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the publish guard.

These live in a file on purpose: the guard blocks any *shell command* that
matches a publishing pattern, so testing it from the shell is impossible —
the test command itself would be blocked. File content is not a command.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from publish_guard import classify, main, standing_match, strip_heredocs  # noqa: E402

PUBLISH_CMD = "npm " + "publish"  # split so this file never contains the literal
BROADCAST_FLAG = "--" + "broadcast"


def decision(command: str, capsys: pytest.CaptureFixture[str]) -> dict:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    sys.stdin = __import__("io").StringIO(payload)
    main()
    return json.loads(capsys.readouterr().out)


def test_expose_tier_is_blocked() -> None:
    tier, _ = classify(f"XX-FAKE {PUBLISH_CMD}-DOES-NOT-EXIST")
    assert tier == "expose"
    tier, _ = classify(f"XX-FAKE forge script X.s.sol {BROADCAST_FLAG}")
    assert tier == "expose"
    tier, _ = classify("gh repo edit x --visibility public")
    assert tier == "expose"


def test_routine_tier_passes_with_warning() -> None:
    tier, _ = classify("git push origin main")
    assert tier == "routine"
    tier, _ = classify("npx wrangler deploy")
    assert tier == "routine"


def test_private_repo_creation_is_not_exposure() -> None:
    assert classify("gh repo create foo --private") is None


def test_harmless_commands_are_ignored() -> None:
    assert classify("ls -la") is None
    assert classify("pytest tests/") is None


def test_heredoc_body_is_not_a_command() -> None:
    """Writing a file that mentions a blocked command is not running it."""
    command = f"cat > doc.md <<'EOF'\nRun {PUBLISH_CMD} to release\nEOF"
    assert classify(strip_heredocs(command)) is None
    # ...but an actual invocation after the heredoc still counts.
    command_with_real = f"cat > doc.md <<'EOF'\ntext\nEOF\n{PUBLISH_CMD}"
    assert classify(strip_heredocs(command_with_real)) is not None


def test_standing_authorization_recognizes_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "publish_guard.load_standing",
        lambda: [{"kind": "docker", "identifier": "ghcr.io/me/app", "authorized_at": 0}],
    )
    assert standing_match("docker push ghcr.io/me/app:v2") == "docker:ghcr.io/me/app"
    assert standing_match("docker push ghcr.io/someone-else/app:v2") is None


def test_blocked_command_denies(capsys: pytest.CaptureFixture[str]) -> None:
    result = decision(f"XX-FAKE {PUBLISH_CMD}-DOES-NOT-EXIST", capsys)
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_routine_command_allows_with_message(capsys: pytest.CaptureFixture[str]) -> None:
    result = decision("git push origin main", capsys)
    assert "hookSpecificOutput" not in result
    assert "systemMessage" in result


def test_standing_target_allows(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "publish_guard.load_standing",
        lambda: [{"kind": "docker", "identifier": "ghcr.io/me/app", "authorized_at": 0}],
    )
    result = decision("docker push ghcr.io/me/app:v3", capsys)
    assert "hookSpecificOutput" not in result
    assert "recorrente" in result["systemMessage"]
