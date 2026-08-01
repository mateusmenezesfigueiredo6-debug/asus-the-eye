"""Command-line interface."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

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
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
