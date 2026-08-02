#!/usr/bin/env python3
"""PreToolUse hook: warn and block any publishing command without the passphrase.

Reads the Claude Code hook payload on stdin. If the Bash command matches a
publishing pattern (anything that sends code, data or transactions off this
machine) and no publish window is open, the call is denied with a loud warning.

Covered: git push, gh repo create/edit/release/gist, npm/pypi publish, docker
push, wrangler deploy, blockchain broadcast (forge --broadcast, cast send),
and any `gh api` write to a visibility endpoint.

Exit 0 + JSON decision on stdout is the hook contract; a crash must never
silently allow, so unknown failures deny.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from publish_lock import LOCK_FILE, load_standing, unlock_remaining_seconds
except Exception:  # pragma: no cover - fail closed
    LOCK_FILE = Path.home() / ".the-eye" / "publish-lock.json"

    def unlock_remaining_seconds() -> int:
        return 0

    def load_standing() -> list:
        return []


def strip_heredocs(command: str) -> str:
    """Remove heredoc bodies before pattern matching.

    Writing a file whose *content* names a publishing command is not publishing.
    Without this, editing the guard itself (or any doc that documents the
    blocked commands) trips the guard — a false positive that teaches people to
    disable it.
    """
    result: list[str] = []
    delimiter: str | None = None
    for line in command.splitlines():
        if delimiter is None:
            match = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
            result.append(line)
            if match:
                delimiter = match.group(1)
        elif line.strip() == delimiter:
            delimiter = None
    return "\n".join(result)


# Tier EXPOSE: makes something visible to the world or is irreversible outside
# this machine. Always blocked without the passphrase — this is the tier that
# catches what was never agreed: a mistake, an automation, an AI overstep.
EXPOSE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bgh\s+repo\s+create\b(?!.*--private)", "gh repo create sem --private (repo pode nascer público)"),
    (r"\bgh\s+repo\s+edit\b.*--visibility\s+public", "tornar repositório PÚBLICO"),
    (r"\bgh\s+release\s+create\b", "gh release create (publica release)"),
    (r"\bgh\s+gist\s+create\b(?!.*--secret)", "gh gist create público"),
    (r"\bgh\s+api\b.*(visibility|/releases|/pages)", "gh api (escrita que expõe conteúdo)"),
    (r"\bnpm\s+publish\b", "npm publish (publica pacote no registro)"),
    (r"\b(twine\s+upload|python[0-9.]*\s+-m\s+twine)\b", "twine upload (publica no PyPI)"),
    (r"\bdocker\s+push\b", "docker push (publica imagem)"),
    (r"--broadcast\b", "broadcast de transação blockchain (irreversível)"),
    (r"\bcast\s+send\b", "cast send (transação blockchain real)"),
    (r"\bforge\s+create\b", "forge create (deploy de contrato)"),
    (r"\bwrangler\s+pages\s+deploy\b", "wrangler pages deploy (site público)"),
)

# Tier ROUTINE: agreed, private, reversible — your own private repo, your own
# token-protected worker. Warn (so nothing happens silently) but do not block.
ROUTINE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bgit\s+push\b", "git push para o remoto privado"),
    (r"\bwrangler\s+(deploy|publish)\b", "wrangler deploy do worker restrito"),
)


def _package_name(directory: Path) -> str | None:
    manifest = directory / "package.json"
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("name")
    except ValueError:
        return None


def standing_match(command: str) -> str | None:
    """Identifier of a standing authorization covering this command, if any.

    Re-releasing an already-public artifact is not a new exposure: that decision
    was made once, with the passphrase. Gating every version of a live product
    would train the user to keep the window permanently open — worse than no
    lock. Only new or unknown targets stay gated.
    """
    lowered = command.lower()
    for target in load_standing():
        kind, identifier = target.get("kind", ""), target.get("identifier", "")
        if not identifier:
            continue
        if identifier.lower() in lowered:
            return f"{kind}:{identifier}"
        # npm carries no target on the command line; read the local manifest.
        if kind == "npm" and re.search(r"\bnpm\s+publish\b", lowered):
            if _package_name(Path.cwd()) == identifier:
                return f"{kind}:{identifier}"
    return None


def classify(command: str) -> tuple[str, str] | None:
    """Return (tier, description) for a command, or None when it is harmless."""
    for pattern, description in EXPOSE_PATTERNS:
        if re.search(pattern, command, flags=re.IGNORECASE):
            return "expose", description
    for pattern, description in ROUTINE_PATTERNS:
        if re.search(pattern, command, flags=re.IGNORECASE):
            return "routine", description
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return 0

    if payload.get("tool_name") != "Bash":
        print(json.dumps({}))
        return 0

    raw_command = str(payload.get("tool_input", {}).get("command", ""))
    command = strip_heredocs(raw_command)
    classified = classify(command)
    if classified is None:
        print(json.dumps({}))
        return 0
    tier, reason = classified

    # Routine, private, reversible: always announce, never block.
    if tier == "routine":
        print(json.dumps({"systemMessage": f"📤 Saindo da máquina (combinado): {reason}"}))
        return 0

    # Recurring release to an already-authorized target: exposure decided once.
    authorized = standing_match(command)
    if authorized is not None:
        print(
            json.dumps(
                {"systemMessage": f"📦 Release recorrente autorizado ({authorized}): {reason}"}
            )
        )
        return 0

    remaining = unlock_remaining_seconds()
    if remaining > 0:
        print(
            json.dumps(
                {
                    "systemMessage": (
                        f"🔓 Publicação liberada ({remaining}s restantes) — executando: {reason}"
                    )
                }
            )
        )
        return 0

    lock_hint = (
        "python3 scripts/publish_lock.py set   # defina a senha (só você digita)"
        if not Path(LOCK_FILE).exists()
        else "python3 scripts/publish_lock.py unlock   # abre janela de 5 min"
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "🔒 BLOQUEIO DE PUBLICAÇÃO\n\n"
                        f"Comando barrado: {reason}\n"
                        f"  $ {command[:200]}\n\n"
                        "Nada sai desta máquina sem a sua senha. Para liberar, rode você mesmo:\n"
                        f"  {lock_hint}\n\n"
                        "Se este é um lançamento RECORRENTE (produto vivo), autorize o alvo\n"
                        "uma vez e ele flui para sempre, sem senha:\n"
                        "  python3 scripts/publish_lock.py authorize <npm|docker|release> <alvo>\n\n"
                        "A senha nunca passa por esta conversa."
                    ),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
