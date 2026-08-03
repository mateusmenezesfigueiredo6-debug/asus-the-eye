#!/usr/bin/env python3
"""Portões de lançamento executáveis (ver RELEASE_PROTOCOL.md).

    python3 scripts/release_check.py L2            # roda os portões da classe
    python3 scripts/release_check.py L3 --publish  # e ancora o registro no ledger

Cada classe herda os portões das anteriores. O que só um humano pode atestar
(RIPD, aprovação jurídica, intervalo de 24h) aparece como MANUAL — o script
nunca marca esses como aprovados sozinho; ele os lista para você confirmar.

Saída: registro de lançamento com hash. Falha = sai com código 1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from asus_theye.audit.remote_ledger import _ledger_token, publish_event  # noqa: E402

WORKER_URL = "https://the-eye-audit-staging.mateusmenezesfigueiredo6.workers.dev"
CLASSES = ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]


def run(args: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str]:
    try:
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=600)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except Exception as error:  # noqa: BLE001 - qualquer falha é reprovação
        return 1, str(error)


# ---------------------------------------------------------------- portões L0/L1


def gate_tests() -> tuple[bool, str]:
    code, out = run([str(REPO_ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "tests/"])
    tail = out.strip().splitlines()[-1] if out.strip() else "sem saída"
    return code == 0, tail


def gate_lint() -> tuple[bool, str]:
    code, out = run([str(REPO_ROOT / ".venv/bin/ruff"), "check", "src/asus_theye/", "scripts/"])
    return code == 0, "limpo" if code == 0 else out.strip().splitlines()[-1]


def gate_no_tracked_secrets() -> tuple[bool, str]:
    code, out = run(["git", "ls-files"])
    suspicious = [
        line
        for line in out.splitlines()
        if any(token in line.lower() for token in (".env", "secret", "token", ".key", ".pem"))
        and not line.endswith(".example")
    ]
    return not suspicious, "nenhum" if not suspicious else f"suspeitos: {suspicious[:3]}"


def gate_clean_worktree() -> tuple[bool, str]:
    _, out = run(["git", "status", "--porcelain"])
    dirty = [line for line in out.splitlines() if not line.startswith("??")]
    return not dirty, "limpo" if not dirty else f"{len(dirty)} arquivo(s) modificado(s)"


# ------------------------------------------------------------------- portões L2


def gate_endpoints_closed() -> tuple[bool, str]:
    paths = ("/health", "/events?tenant=tenant-demo", "/batches?tenant=tenant-demo")
    codes = []
    for path in paths:
        try:
            request = urllib.request.Request(f"{WORKER_URL}{path}", headers={"user-agent": "release-check/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                codes.append(response.status)
        except urllib.error.HTTPError as error:
            codes.append(error.code)
        except Exception:
            codes.append(0)
    closed = all(code == 401 for code in codes)
    return closed, f"anônimo → {codes} (esperado todos 401)"


def gate_secret_in_vault() -> tuple[bool, str]:
    code, out = run(["npx", "wrangler", "secret", "list"], cwd=REPO_ROOT / "infra/cloudflare/staging")
    ok = code == 0 and "AUDIT_INGEST_TOKEN" in out
    return ok, "AUDIT_INGEST_TOKEN no cofre" if ok else "segredo não confirmado no cofre"


def gate_chain_integrity() -> tuple[bool, str]:
    code, out = run([str(REPO_ROOT / ".venv/bin/python"), "scripts/leak_check.py"])
    last = out.strip().splitlines()[-2] if out.strip() else "sem saída"
    return code == 0, last.strip()


# ------------------------------------------------------------------- portões L3+


def gate_no_pii_onchain_policy() -> tuple[bool, str]:
    """A ancoragem só pode publicar raiz/hashes — nunca conteúdo."""
    adr = REPO_ROOT / "docs/adr/ADR-001-OFFCHAIN-ONCHAIN.md"
    return adr.exists(), "ADR-001 presente (off-chain data / on-chain proof)"


def gate_broadcast_disabled_by_default() -> tuple[bool, str]:
    config = (REPO_ROOT / "infra/cloudflare/staging/wrangler.toml").read_text(encoding="utf-8")
    ok = 'BLOCKCHAIN_BROADCAST_ENABLED = "false"' in config
    return ok, "broadcast desligado por padrão" if ok else "broadcast NÃO está desligado por padrão"


MANUAL_GATES: dict[str, list[str]] = {
    "L3": [
        "A chave privada será usada por VOCÊ, nunca pela IA",
        "Contrato revisado; endereço e bytecode registrados antes do envio",
        "Você aceita que raiz, horário e endereço ficam públicos para sempre",
    ],
    "L4": [
        "RIPD/DPIA concluído por profissional humano",
        "Base legal mapeada por operação (+ teste de balanceamento onde couber)",
        "Processo de correção e contestação operante",
        "Plano de incidente e rollback com dados reais",
    ],
    "L5": [
        "Passaram-se 24h desde a decisão de tornar público",
        "Histórico completo do git varrido por segredos (não só o HEAD)",
        "README e relatórios revisados quanto ao que expõem",
        "Você está conscientemente excepcionando a regra 'repos sempre privados'",
    ],
    "L6": [
        "Decisão de governança formal, documentada e separada",
        "Aprovações executiva, jurídica, de privacidade, segurança e financeira",
    ],
}

AUTO_GATES: dict[str, list[tuple[str, Callable[[], tuple[bool, str]]]]] = {
    "L0": [
        ("testes verdes", gate_tests),
        ("lint limpo", gate_lint),
    ],
    "L1": [
        ("nenhum segredo rastreado pelo git", gate_no_tracked_secrets),
        ("árvore de trabalho limpa", gate_clean_worktree),
    ],
    "L2": [
        ("endpoints fechados a estranhos", gate_endpoints_closed),
        ("segredo no cofre do provedor", gate_secret_in_vault),
        ("integridade da cadeia (tripla checagem)", gate_chain_integrity),
    ],
    "L3": [
        ("política off-chain/on-chain documentada", gate_no_pii_onchain_policy),
        ("broadcast desligado por padrão", gate_broadcast_disabled_by_default),
    ],
    "L4": [],
    "L5": [],
    "L6": [],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Portões de lançamento do THE EYE")
    parser.add_argument("release_class", choices=CLASSES)
    parser.add_argument("--publish", action="store_true", help="ancorar o registro no ledger")
    parser.add_argument("--ledger-url", default=WORKER_URL)
    args = parser.parse_args()

    target_index = CLASSES.index(args.release_class)
    applicable = CLASSES[: target_index + 1]

    print("=" * 62)
    print(f"PORTÕES DE LANÇAMENTO — classe {args.release_class}")
    print("=" * 62)

    results: list[dict] = []
    failed = 0
    for level in applicable:
        gates = AUTO_GATES.get(level, [])
        if not gates:
            continue
        print(f"\n[{level}]")
        for name, check in gates:
            passed, detail = check()
            print(f"  {'OK   ' if passed else 'FALHA'}  {name}: {detail}")
            results.append({"level": level, "gate": name, "passed": passed, "detail": detail})
            if not passed:
                failed += 1

    manual: list[str] = []
    for level in applicable:
        manual.extend(f"[{level}] {item}" for item in MANUAL_GATES.get(level, []))
    if manual:
        print("\n[MANUAL] só você pode atestar — o script nunca marca sozinho:")
        for item in manual:
            print(f"  [ ] {item}")

    _, commit = run(["git", "rev-parse", "--short", "HEAD"])
    record = {
        "release_class": args.release_class,
        "commit": commit.strip(),
        "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "automatic_gates": results,
        "automatic_failures": failed,
        "manual_gates_pending_human_attestation": manual,
        "verdict": "gates_passed" if failed == 0 else "gates_failed",
    }
    record["record_hash_sha256"] = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    out_dir = REPO_ROOT / "reports/releases"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"release-{args.release_class}-{record['record_hash_sha256'][:12]}.json"
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 62)
    print(f"VEREDITO: {record['verdict'].upper()} ({failed} falha(s) automática(s))")
    if manual:
        print(f"         + {len(manual)} atestado(s) humano(s) pendente(s)")
    print(f"Registro: {target.relative_to(REPO_ROOT)}")

    if args.publish and _ledger_token():
        receipt = publish_event(
            {
                "tenant_id": "tenant-demo",
                "idempotency_key": f"release-{record['record_hash_sha256'][:32]}",
                "event_type": "release.checked",
                "resource_type": "release_record",
                "resource_id_pseudonymous": f"rel-{record['record_hash_sha256'][:16]}",
                "payload": {
                    "release_class": record["release_class"],
                    "commit": record["commit"],
                    "verdict": record["verdict"],
                    "automatic_failures": failed,
                    "manual_pending": len(manual),
                    "record_hash_sha256": record["record_hash_sha256"],
                },
            },
            args.ledger_url,
        )
        print(f"Ledger:   sequência {receipt['sequence']}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
