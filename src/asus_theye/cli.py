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
    batch = subcommands.add_parser("batch", help="build a Merkle batch of pending ledger events")
    batch.add_argument("--ledger-url", default=os.environ.get("THE_EYE_LEDGER_URL", ""))
    batch.add_argument("--tenant", default=DEFAULT_TENANT)
    batch.add_argument("--publish", action="store_true", help="store the batch on the ledger")
    batch.add_argument(
        "--proofs-out",
        type=Path,
        default=Path("reports/audit/proofs"),
        help="directory for the manifest and inclusion proofs",
    )
    source_graph = subcommands.add_parser(
        "source-graph", help="grafo de fontes: cobertura, lacunas e relatórios da Phase C"
    )
    source_graph.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="não toca a rede (padrão; o Estágio 1 é inteiramente offline)",
    )
    source_graph.add_argument("--reports", action="store_true", help="escrever os 3 relatórios")
    source_graph.add_argument("--ledger-url", default=os.environ.get("THE_EYE_LEDGER_URL", ""))
    source_graph.add_argument("--tenant", default=DEFAULT_TENANT)
    source_graph.add_argument("--publish", action="store_true", help="ancorar o snapshot no ledger")
    chart = subcommands.add_parser("chart", help="Mistress Chart — projetos e nichos medidos")
    chart.add_argument("--html", type=Path, default=Path("reports/chart/mistress-chart.html"))
    chart.add_argument("--json", dest="json_out", type=Path, default=Path("reports/chart/snapshot.json"))
    chart.add_argument("--ledger-url", default=os.environ.get("THE_EYE_LEDGER_URL", ""))
    chart.add_argument("--tenant", default=DEFAULT_TENANT)
    chart.add_argument("--publish", action="store_true", help="ancorar o hash do snapshot no ledger")
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
        print(f"\nClassical:\nscore: {classical['score']}\ntime: {classical['execution_time_ms']:.3f} ms")
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
    if args.command == "batch":
        from asus_theye.audit.batching import batch_pending_events

        if not args.ledger_url:
            print("batch: --ledger-url or THE_EYE_LEDGER_URL required")
            return 1
        outcome = batch_pending_events(args.ledger_url, args.tenant, publish=args.publish)
        if outcome["status"] == "up_to_date":
            print(f"Batch: up to date (last batched sequence {outcome['last_batched_sequence']})")
            return 0
        manifest = outcome["manifest"]
        args.proofs_out.mkdir(parents=True, exist_ok=True)
        target = args.proofs_out / f"batch-{manifest['batch_id']}.json"
        target.write_text(
            json.dumps({"manifest": manifest, "proofs": outcome["proofs"]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("==========================")
        print("MERKLE BATCH")
        print("==========================")
        print(f"\nevents: {manifest['event_count']} (seq {manifest['first_sequence']}-{manifest['last_sequence']})")
        print(f"merkle_root: {manifest['merkle_root']}")
        print(f"previous_batch_root: {manifest['previous_batch_root']}")
        print(f"manifest_hash: {manifest['manifest_hash_sha256']}")
        print(f"status: {outcome['status']}")
        print(f"\nProofs:\n{target}")
        return 0
    if args.command == "source-graph":
        from asus_theye.audit.remote_ledger import publish_event
        from asus_theye.source_graph import (
            build_coverage,
            coverage_by_track,
            graph_built_event,
            write_reports,
        )

        coverage = build_coverage([])
        tracks = coverage_by_track(coverage)
        print("=" * 62)
        print("GRAFO DE FONTES — COBERTURA")
        print("=" * 62)
        print(f"\nmetodologia: {coverage['methodology_version']}")
        print(f"snapshot:    {coverage['snapshot_hash_sha256']}\n")
        for track, data in tracks.items():
            reasons = ", ".join(f"{k}×{v}" for k, v in sorted(data["blocking_reasons"].items()))
            print(
                f"  {track:14s} {data['qualified']:4d}/{data['target']:5d}  {data['coverage_pct']:5.1f}%  [{reasons}]"
            )
        print("\nLACUNAS")
        for gap in coverage["gaps"]:
            print(f"  [{gap['blocking_reason']}] {gap['description']}")
        if args.reports:
            for path in write_reports(coverage, tracks):
                print(f"\nRelatório: {path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path}")
        if args.publish:
            if not args.ledger_url:
                print("\nsource-graph: --publish requer --ledger-url ou THE_EYE_LEDGER_URL")
                return 1
            snapshot = {
                "sources_total": 0,
                "by_category": {e["category_id"]: e["qualified_count"] for e in coverage["by_category"]},
                "methodology_version": coverage["methodology_version"],
            }
            receipt = publish_event(graph_built_event(snapshot, commit="", tenant_id=args.tenant), args.ledger_url)
            print(f"\nLedger: sequência {receipt['sequence']}")
        return 0
    if args.command == "chart":
        from asus_theye.audit.remote_ledger import publish_event
        from asus_theye.chart import build_chart, chart_snapshot_hash, render_html, render_text

        events = None
        if args.ledger_url:
            from asus_theye.audit.batching import fetch_events

            events = fetch_events(args.ledger_url, args.tenant)
        snapshot = build_chart(events)
        snapshot_hash = chart_snapshot_hash(snapshot)
        print(render_text(snapshot, snapshot_hash))

        for target, content in (
            (args.json_out, json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"),
            (args.html, render_html(snapshot, snapshot_hash)),
        ):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        print(f"\nHTML: {args.html}\nJSON: {args.json_out}")

        if args.publish:
            if not args.ledger_url:
                print("chart: --publish requer --ledger-url ou THE_EYE_LEDGER_URL")
                return 1
            receipt = publish_event(
                {
                    "tenant_id": args.tenant,
                    "idempotency_key": f"chart-{snapshot_hash[:32]}",
                    "event_type": "chart.snapshot",
                    "resource_type": "mistress_chart",
                    "resource_id_pseudonymous": f"chart-{snapshot_hash[:16]}",
                    "payload": {
                        "commit": snapshot["commit"],
                        "snapshot_hash_sha256": snapshot_hash,
                        **snapshot["totals"],
                    },
                },
                args.ledger_url,
            )
            print(f"Ledger: sequência {receipt['sequence']}")
        return 0
    if args.command == "quantum":
        from asus_theye.benchmark.ibm_backend import dry_run, run_on_hardware
        from asus_theye.problem import load_demo_problem

        problem = load_demo_problem()
        if args.execute:
            outcome = run_on_hardware(problem, layers=args.layers, shots=args.shots, backend_name=args.backend)
        else:
            outcome = dry_run(problem, layers=args.layers, shots=args.shots)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
