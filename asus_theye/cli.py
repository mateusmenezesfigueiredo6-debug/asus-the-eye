"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path

from asus_theye.audit.remote_ledger import DEFAULT_TENANT, publish_benchmark_report
from asus_theye.audit.verifier import verify_file
from asus_theye.benchmark.runner import run_benchmark_suite


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asus-theye")
    subcommands = parser.add_subparsers(dest="command", required=True)
    benchmark = subcommands.add_parser("benchmark", help="run the local benchmark suite")
    benchmark.add_argument("--output-dir", type=Path, default=Path("reports/benchmark"))
    benchmark.add_argument("--shots", type=int, default=1_024)
    benchmark.add_argument("--layers", type=int, default=2)
    benchmark.add_argument("--seed", type=int, default=42)
    benchmark.add_argument("--stability-runs", type=int, default=10)
    benchmark.add_argument(
        "--publish",
        action="store_true",
        help="publish the report summary to the remote audit ledger (opt-in)",
    )
    benchmark.add_argument(
        "--ledger-url",
        default=os.environ.get("THE_EYE_LEDGER_URL", ""),
        help="audit ledger base URL (or THE_EYE_LEDGER_URL env var)",
    )
    benchmark.add_argument("--tenant", default=DEFAULT_TENANT)
    verify = subcommands.add_parser("audit-verify", help="verify an offline audit JSON document")
    verify.add_argument("input", type=Path)
    verify.add_argument("--receipt", type=Path)
    llm = subcommands.add_parser("llm", help="call the audited local LLM (Ollama)")
    llm.add_argument("prompt")
    llm.add_argument("--system")
    llm.add_argument("--model", default=None)
    llm.add_argument("--temperature", type=float, default=0.2)
    llm.add_argument(
        "--publish",
        action="store_true",
        help="anchor the call record (hashes only) on the remote audit ledger",
    )
    llm.add_argument("--ledger-url", default=os.environ.get("THE_EYE_LEDGER_URL", ""))
    llm.add_argument("--tenant", default=DEFAULT_TENANT)
    extract = subcommands.add_parser(
        "extract-decision",
        help="extract schema-validated procedural facts from a public decision text file",
    )
    extract.add_argument("input", type=Path, help="text file with the public decision")
    quantum = subcommands.add_parser("quantum", help="IBM Quantum adapter (gated)")
    quantum.add_argument(
        "--execute", action="store_true", help="submit a real QPU job (requires THE_EYE_IBM_EXECUTE=1)"
    )
    quantum.add_argument("--backend", default=None)
    quantum.add_argument("--shots", type=int, default=1_024)
    quantum.add_argument("--layers", type=int, default=2)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "benchmark":
        report, path = run_benchmark_suite(
            output_dir=args.output_dir,
            shots=args.shots,
            layers=args.layers,
            seed=args.seed,
            stability_runs=args.stability_runs,
        )
        results = report["results"]
        metrics = report["metrics"]
        print("==========================")
        print("ASUS THE EYE BENCHMARK")
        print("==========================")
        classical = results["classical"]
        qubo = results["qubo"]
        qaoa = results["qaoa"]
        print(
            f"\nClassical:\nscore: {classical['score']}"
            f"\ntime: {classical['execution_time_ms']:.3f} ms"
        )
        print(f"\nQUBO:\nvariables: {qubo['variables']}\ntime: {qubo['execution_time_ms']:.3f} ms")
        print(f"\nQAOA:\nshots: {qaoa['shots']}\nscore: {qaoa['score']}")
        print(f"\nQAR: {metrics['qar']['qar']}")
        print(f"\nReport:\n{path}")
        if args.publish:
            if not args.ledger_url:
                print("\nLedger: --publish requires --ledger-url or THE_EYE_LEDGER_URL")
                return 1
            receipt = publish_benchmark_report(report, args.ledger_url, args.tenant)
            deduplicated = receipt.get("deduplicated", False)
            print(
                f"\nLedger:\nsequence: {receipt['sequence']}"
                f"\nevent_hash: {receipt['event_hash_sha256']}"
                f"\ndeduplicated: {deduplicated}"
            )
        return 0
    if args.command == "audit-verify":
        receipt = verify_file(args.input, args.receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0 if receipt["status"] in {"valid", "not_anchored", "anchor_unconfirmed"} else 1
    if args.command == "llm":
        from asus_theye.llm import AuditedLocalLLM, OllamaClient

        if args.publish and not args.ledger_url:
            print("llm: --publish requires --ledger-url or THE_EYE_LEDGER_URL")
            return 1
        client = OllamaClient(model=args.model) if args.model else OllamaClient()
        llm = AuditedLocalLLM(
            client=client,
            ledger_url=args.ledger_url if args.publish else None,
            tenant_id=args.tenant,
        )
        outcome = llm.chat(args.prompt, system=args.system, temperature=args.temperature)
        print(outcome["content"])
        record = outcome["audit_record"]
        print(
            f"\n[audit] model={record['model']} duration_ms={record['duration_ms']}"
            f"\n[audit] record_hash={record['record_hash_sha256']}"
        )
        if outcome["ledger_receipt"] is not None:
            print(f"[audit] ledger_sequence={outcome['ledger_receipt']['sequence']}")
        return 0
    if args.command == "extract-decision":
        from asus_theye.decision_context import extract_decision_fields

        fields = extract_decision_fields(args.input.read_text(encoding="utf-8"))
        print(json.dumps(fields, ensure_ascii=False, indent=2))
        return 0
    if args.command == "quantum":
        from asus_theye.benchmark.ibm_backend import dry_run, run_on_hardware
        from asus_theye.problem import load_demo_problem

        problem = load_demo_problem()
        if args.execute:
            outcome = run_on_hardware(
                problem, layers=args.layers, shots=args.shots, backend_name=args.backend
            )
        else:
            outcome = dry_run(problem, layers=args.layers, shots=args.shots)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
