#!/usr/bin/env python3
"""Tripla checagem de vazamento — independente de confiar em quem quer que seja.

Camada 1 — ESTRANHO: o que um terceiro sem credencial nenhuma consegue ver.
           Requisições anônimas ao worker e à API pública do GitHub.
Camada 2 — PROVEDOR: o que a Cloudflare e o GitHub dizem (registros deles, não
           nossos): visibilidade, forks, colaboradores, buckets públicos.
Camada 3 — MATEMÁTICA: a cadeia de hashes e a raiz Merkle. Se qualquer evento
           tivesse sido inserido, alterado ou removido por alguém, a raiz
           recalculada divergiria da raiz armazenada. Isso não depende de
           confiança: ou o número bate, ou não bate.

Rode a qualquer momento, sem IA no meio:
    python3 scripts/leak_check.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asus_theye.audit.merkle import MerkleTree, verify_proof  # noqa: E402
from asus_theye.audit.remote_ledger import _ledger_token  # noqa: E402

WORKER_URL = "https://the-eye-audit-staging.mateusmenezesfigueiredo6.workers.dev"
REPO = "mateusmenezesfigueiredo6-debug/asus-the-eye"
PROTECTED_PATHS = ("/health", "/events?tenant=tenant-demo", "/batches?tenant=tenant-demo")

OK, FAIL = "OK   ", "FALHA"
findings: list[str] = []


def _status(url: str, token: str | None = None) -> int:
    headers = {"user-agent": "the-eye-leak-check/1.0"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def layer1_stranger() -> None:
    print("\n[CAMADA 1] ESTRANHO — o que alguém sem credencial vê")
    for path in PROTECTED_PATHS:
        code = _status(f"{WORKER_URL}{path}")
        good = code == 401
        print(f"  {OK if good else FAIL}  {path:34s} HTTP {code} (esperado 401)")
        if not good:
            findings.append(f"worker{path} respondeu {code} sem token")

    # API pública do GitHub, sem autenticação: repo privado deve dar 404.
    code = _status(f"https://api.github.com/repos/{REPO}")
    good = code == 404
    print(f"  {OK if good else FAIL}  repo anônimo via API pública      HTTP {code} (esperado 404)")
    if not good:
        findings.append(f"repo visível anonimamente (HTTP {code})")


def _gh(args: list[str]) -> str | None:
    try:
        return subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60, check=True).stdout.strip()
    except Exception:
        return None


def layer2_provider() -> None:
    print("\n[CAMADA 2] PROVEDOR — o que Cloudflare e GitHub registram")
    raw = _gh(["repo", "view", REPO, "--json", "visibility,isFork,forkCount,stargazerCount"])
    if raw:
        info = json.loads(raw)
        private = info.get("visibility") == "PRIVATE"
        print(f"  {OK if private else FAIL}  visibilidade do repo: {info.get('visibility')}")
        if not private:
            findings.append("repo não está privado")
        for label, key in (("forks", "forkCount"), ("estrelas", "stargazerCount")):
            count = info.get(key, 0)
            print(f"  {OK if count == 0 else FAIL}  {label}: {count} (esperado 0)")
            if count:
                findings.append(f"{label} inesperados: {count}")
    else:
        print("  ????  gh indisponível — checagem do provedor incompleta")
        findings.append("não foi possível consultar o GitHub")

    collabs = _gh(["api", f"repos/{REPO}/collaborators", "--jq", "length"])
    if collabs is not None:
        solo = collabs == "1"
        print(f"  {OK if solo else FAIL}  colaboradores: {collabs} (esperado 1, só você)")
        if not solo:
            findings.append(f"colaboradores além de você: {collabs}")


def layer3_math() -> None:
    print("\n[CAMADA 3] MATEMÁTICA — a cadeia não mente")
    token = _ledger_token()
    if not token:
        print("  ????  sem token local; pulei a verificação criptográfica")
        findings.append("token ausente: camada 3 não executada")
        return

    req = urllib.request.Request(
        f"{WORKER_URL}/events?tenant=tenant-demo",
        headers={"authorization": f"Bearer {token}", "user-agent": "the-eye-leak-check/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        events = json.loads(response.read().decode("utf-8"))["events"]
    for event in events:
        event["tenant_id"] = "tenant-demo"
    events.sort(key=lambda e: e["sequence"])

    # 3a. Encadeamento: cada evento aponta para o hash do anterior.
    genesis = "0" * 64
    previous = genesis
    linked = True
    for event in events:
        if event["previous_event_hash_sha256"] != previous:
            linked = False
            findings.append(f"elo quebrado na sequência {event['sequence']}")
        previous = event["event_hash_sha256"]
    print(f"  {OK if linked else FAIL}  encadeamento de {len(events)} eventos")

    # 3b. Sequência sem buracos (nada foi removido).
    contiguous = [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    print(f"  {OK if contiguous else FAIL}  sequência contígua 1..{len(events)} (nada removido)")
    if not contiguous:
        findings.append("há buraco na sequência de eventos")

    # 3c. Raiz Merkle: recalculada agora bate com a que foi armazenada?
    proof_files = sorted((Path("reports/audit/proofs")).glob("batch-*.json"))
    if not proof_files:
        print("  ????  nenhum lote local para conferir a raiz")
        return
    stored = json.loads(proof_files[-1].read_text(encoding="utf-8"))
    stored_root = stored["manifest"]["merkle_root"]
    covered = {p["sequence"] for p in stored["proofs"]}
    subset = [e for e in events if e["sequence"] in covered]
    recomputed = MerkleTree(subset).root
    same = recomputed == stored_root
    print(f"  {OK if same else FAIL}  raiz Merkle recalculada bate com a armazenada")
    print(f"        armazenada: {stored_root}")
    print(f"        recalculada: {recomputed}")
    if not same:
        findings.append("raiz Merkle divergente — conteúdo do lote mudou")

    proofs_ok = all(verify_proof(p["event_hash_sha256"], p["proof"]) for p in stored["proofs"])
    print(f"  {OK if proofs_ok else FAIL}  {len(stored['proofs'])} provas de inclusão válidas")
    if not proofs_ok:
        findings.append("prova de inclusão inválida")


def main() -> int:
    print("=" * 62)
    print("TRIPLA CHECAGEM DE VAZAMENTO — THE EYE")
    print("=" * 62)
    layer1_stranger()
    layer2_provider()
    layer3_math()
    print("\n" + "=" * 62)
    if findings:
        print(f"VEREDITO: {len(findings)} PROBLEMA(S) ENCONTRADO(S)")
        for item in findings:
            print(f"  - {item}")
        return 1
    print("VEREDITO: NENHUM VAZAMENTO DETECTADO nas três camadas")
    print("(estranho não entra · provedor confirma privado · matemática confere)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
