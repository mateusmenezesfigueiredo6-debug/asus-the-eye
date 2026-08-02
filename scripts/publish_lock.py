#!/usr/bin/env python3
"""Publish lock: nothing leaves this machine without a human passphrase.

The passphrase is set by the user in a hidden prompt and never stored in
plaintext, never printed, and never passed through an AI conversation — only a
PBKDF2-SHA256 hash lives on disk. Unlocks are short-lived and single-window.

    python3 scripts/publish_lock.py set        # define/change the passphrase
    python3 scripts/publish_lock.py unlock     # open a 5-minute publish window
    python3 scripts/publish_lock.py status     # show lock state
    python3 scripts/publish_lock.py lock       # close the window immediately
    python3 scripts/publish_lock.py authorize npm @me/pkg   # recurring target: flows freely
    python3 scripts/publish_lock.py list       # show standing authorizations
    python3 scripts/publish_lock.py revoke npm @me/pkg

Standard library only.
"""

from __future__ import annotations

import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from pathlib import Path

LOCK_DIR = Path.home() / ".the-eye"
LOCK_FILE = LOCK_DIR / "publish-lock.json"
UNLOCK_FILE = LOCK_DIR / "publish-unlock.json"
STANDING_FILE = LOCK_DIR / "standing-releases.json"
ITERATIONS = 480_000
DEFAULT_WINDOW_SECONDS = 300


def _derive(passphrase: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, ITERATIONS).hex()


def _write_private(path: Path, payload: dict) -> None:
    LOCK_DIR.mkdir(mode=0o700, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def cmd_set() -> int:
    if LOCK_FILE.exists():
        print("A publish passphrase already exists. Confirm the current one to change it.")
        if not _verify(getpass.getpass("Current passphrase: ")):
            print("Wrong passphrase. Nothing changed.", file=sys.stderr)
            return 1
    first = getpass.getpass("New publish passphrase: ")
    if len(first) < 8:
        print("Passphrase must have at least 8 characters.", file=sys.stderr)
        return 1
    if first != getpass.getpass("Repeat passphrase: "):
        print("Passphrases do not match. Nothing changed.", file=sys.stderr)
        return 1
    salt = secrets.token_bytes(16)
    _write_private(
        LOCK_FILE,
        {"version": 1, "kdf": "pbkdf2_sha256", "iterations": ITERATIONS,
         "salt": salt.hex(), "hash": _derive(first, salt), "created_at": int(time.time())},
    )
    UNLOCK_FILE.unlink(missing_ok=True)
    print("Publish lock armed. Publishing now requires this passphrase.")
    return 0


def _verify(passphrase: str) -> bool:
    if not LOCK_FILE.exists():
        return False
    data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    candidate = hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode("utf-8"), bytes.fromhex(data["salt"]), data["iterations"]
    ).hex()
    return hmac.compare_digest(candidate, data["hash"])


def cmd_unlock(window_seconds: int = DEFAULT_WINDOW_SECONDS) -> int:
    if not LOCK_FILE.exists():
        print("No passphrase set. Run: python3 scripts/publish_lock.py set", file=sys.stderr)
        return 1
    if not _verify(getpass.getpass("Publish passphrase: ")):
        print("Wrong passphrase. Publishing stays blocked.", file=sys.stderr)
        return 1
    expires = int(time.time()) + window_seconds
    _write_private(UNLOCK_FILE, {"expires_at": expires, "window_seconds": window_seconds})
    until = time.strftime("%H:%M:%S", time.localtime(expires))
    print(f"Publishing unlocked for {window_seconds // 60} minutes (until {until}).")
    return 0


def cmd_lock() -> int:
    UNLOCK_FILE.unlink(missing_ok=True)
    print("Publish window closed.")
    return 0


def unlock_remaining_seconds() -> int:
    """Seconds left in the current publish window; 0 when locked."""
    if os.environ.get("THE_EYE_PUBLISH_LOCK_DISABLED") == "1":
        return 0  # the env var must never be a bypass
    if not UNLOCK_FILE.exists():
        return 0
    try:
        expires = int(json.loads(UNLOCK_FILE.read_text(encoding="utf-8"))["expires_at"])
    except (ValueError, KeyError):
        return 0
    return max(0, expires - int(time.time()))


def load_standing() -> list[dict]:
    """Targets whose exposure decision was already made, once, with the passphrase.

    Re-publishing an already-public artifact exposes nothing new: the door opened
    at v1.0.0. Gating every version would train the user to keep the window open
    permanently, which is worse than no lock at all.
    """
    if not STANDING_FILE.exists():
        return []
    try:
        return json.loads(STANDING_FILE.read_text(encoding="utf-8"))["targets"]
    except (ValueError, KeyError):
        return []


def cmd_authorize(kind: str, identifier: str) -> int:
    """Grant standing authorization for a recurring release target."""
    if not LOCK_FILE.exists():
        print("No passphrase set. Run: python3 scripts/publish_lock.py set", file=sys.stderr)
        return 1
    print(f"Standing authorization: {kind} -> {identifier}")
    print("Every future release to THIS target will flow without a passphrase.")
    if not _verify(getpass.getpass("Publish passphrase to confirm: ")):
        print("Wrong passphrase. Nothing authorized.", file=sys.stderr)
        return 1
    targets = load_standing()
    if any(t["kind"] == kind and t["identifier"] == identifier for t in targets):
        print("Already authorized.")
        return 0
    targets.append({"kind": kind, "identifier": identifier, "authorized_at": int(time.time())})
    _write_private(STANDING_FILE, {"targets": targets})
    print("Authorized. New/unknown targets still require the passphrase.")
    return 0


def cmd_revoke(kind: str, identifier: str) -> int:
    targets = [
        t for t in load_standing()
        if not (t["kind"] == kind and t["identifier"] == identifier)
    ]
    _write_private(STANDING_FILE, {"targets": targets})
    print(f"Revoked: {kind} -> {identifier}")
    return 0


def cmd_list() -> int:
    targets = load_standing()
    if not targets:
        print("No standing authorizations. Every exposing release needs the passphrase.")
        return 0
    print("Standing authorizations (recurring releases that flow freely):")
    for target in targets:
        when = time.strftime("%Y-%m-%d", time.localtime(target["authorized_at"]))
        print(f"  {target['kind']:16s} {target['identifier']:40s} desde {when}")
    return 0


def cmd_status() -> int:
    if not LOCK_FILE.exists():
        print("status: NO PASSPHRASE SET — publishing is blocked until you run `set`.")
        return 0
    remaining = unlock_remaining_seconds()
    if remaining:
        print(f"status: UNLOCKED for {remaining}s")
    else:
        print("status: LOCKED — new exposures require the passphrase")
    standing = load_standing()
    print(f"standing authorizations: {len(standing)} (recurring releases that flow freely)")
    return 0


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "status"
    if command == "set":
        return cmd_set()
    if command == "unlock":
        window = int(argv[2]) * 60 if len(argv) > 2 else DEFAULT_WINDOW_SECONDS
        return cmd_unlock(window)
    if command == "lock":
        return cmd_lock()
    if command == "status":
        return cmd_status()
    if command == "authorize" and len(argv) > 3:
        return cmd_authorize(argv[2], argv[3])
    if command == "revoke" and len(argv) > 3:
        return cmd_revoke(argv[2], argv[3])
    if command == "list":
        return cmd_list()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
