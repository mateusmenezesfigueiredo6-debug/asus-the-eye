# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
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
    adjudicate_parser = subcommands.add_parser(
        "adjudicate",
        help="two models, one proposes and the other refutes; disagreement yields CONFLICTED",
    )
    adjudicate_parser.add_argument("question")
    providers = ("local", "ollama", "openai", "chatgpt", "gpt", "anthropic", "claude")
    adjudicate_parser.add_argument("--proposer", default="openai", choices=providers, help="model that answers")
    adjudicate_parser.add_argument("--challenger", default="anthropic", choices=providers, help="model that attacks")
    adjudicate_parser.add_argument("--proposer-model", default=None)
    adjudicate_parser.add_argument("--challenger-model", default=None)
    adjudicate_parser.add_argument("--temperature", type=float, default=0.2)
    adjudicate_parser.add_argument("--ledger-url", default=os.environ.get("THE_EYE_LEDGER_URL", ""))
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
    markets = subcommands.add_parser(
        "markets-reconcile",
        help="reconcilia o scoring do módulo contra o banco medido (asus_teste.duckdb)",
    )
    markets.add_argument(
        "--db",
        type=Path,
        default=None,
        help="caminho do asus_teste.duckdb (padrão: variável de ambiente ASUS_MARKETS_DB)",
    )
    markets.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON em vez da tabela")
    markets.add_argument(
        "--skill",
        action="store_true",
        help="também reporta skill por área contra um palpite constante (janela declarada)",
    )
    markets.add_argument(
        "--baseline",
        type=float,
        default=None,
        help="baseline constante fixo p/ todas as áreas do --skill (padrão: taxa-base de cada área)",
    )
    markets_resolve = subcommands.add_parser(
        "markets-resolve",
        help="resolve mercados vencidos contra a fonte oficial (BCB) e grava no registro do repo",
    )
    markets_resolve.add_argument(
        "--store",
        type=Path,
        default=Path("reports/markets/registro.json"),
        help="registro de mercados (padrão: reports/markets/registro.json)",
    )
    markets_resolve.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_resolve.add_argument(
        "--no-audit",
        action="store_true",
        help="não selar liquidações na cadeia auditável (padrão: sela, idempotente)",
    )
    markets_resolve.add_argument(
        "--sem-sinais",
        action="store_true",
        help="emite o próximo mês sem consultar sinais (padrão: WPAM Focus/IPCA-15; falha de sinal degrada p/ 0,50)",
    )
    markets_emitir = subcommands.add_parser(
        "markets-emitir",
        help="emite o mercado do mês para uma área do registry (juros, cambio, macroeconomia)",
    )
    markets_emitir.add_argument("--area", required=True, help="área do registry de resolvíveis")
    markets_emitir.add_argument("--mes", required=True, help="mês de referência, aaaa-mm")
    markets_emitir.add_argument(
        "--limiar", type=float, required=True, help="limiar DECLARADO da pergunta (critério deriva dele)"
    )
    markets_emitir.add_argument("--store", type=Path, default=Path("reports/markets/registro.json"))
    markets_emitir.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_vintage = subcommands.add_parser(
        "markets-vintage",
        help="arquiva o consenso Focus vigente (vintage) e sela — destrava o Brier comparativo do nowcast",
    )
    markets_vintage.add_argument("--mes", required=True, help="mês de referência, aaaa-mm")
    markets_vintage.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_vintage.add_argument("--no-audit", action="store_true", help="arquiva sem selar na cadeia")
    markets_comparar = subcommands.add_parser(
        "markets-comparar",
        help="mede e SELA a divergência vs comparador (Kalshi) — comparador nunca resolve",
    )
    markets_comparar.add_argument("--claim", required=True, help="claim_id do registro (ex.: MACRO-01::2026-08)")
    markets_comparar.add_argument(
        "--preco",
        type=float,
        default=None,
        help="preço do comparador em [0,1]; omita para buscar AO VIVO na API pública da Kalshi pelo --ticker",
    )
    markets_comparar.add_argument("--ticker", required=True, help="ticker/mercado do comparador (proveniência)")
    markets_comparar.add_argument(
        "--nota", required=True, help="nota de mapeamento: o que o ticker mede e por que é comparável"
    )
    markets_comparar.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_comparar.add_argument("--no-audit", action="store_true", help="não selar na cadeia")
    markets_sinais = subcommands.add_parser(
        "markets-sinais",
        help="mostra os sinais REAIS (Focus/IPCA-15) e a probabilidade WPAM da pergunta do mês",
    )
    markets_sinais.add_argument("--mes", required=True, help="mês de referência, aaaa-mm")
    markets_sinais.add_argument("--limiar", type=float, default=0.5)
    markets_sinais.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_anchor = subcommands.add_parser(
        "markets-anchor",
        help="ancora o lote Merkle da corrente na Base Sepolia (padrão: ensaio offline)",
    )
    markets_anchor.add_argument(
        "--eventos",
        type=Path,
        default=Path("reports/markets/eventos.jsonl"),
        help="corrente versionada de eventos selados",
    )
    markets_anchor.add_argument(
        "--execute",
        action="store_true",
        help="broadcast REAL na Base Sepolia (exige THE_EYE_ANCHOR_EXECUTE=1 e carteira fundada)",
    )
    markets_anchor.add_argument(
        "--rpc", default=os.environ.get("THE_EYE_ANCHOR_RPC", ""), help="RPC (padrão: sepolia.base.org)"
    )
    markets_anchor.add_argument(
        "--minimo",
        type=int,
        default=0,
        help="só ancora se houver ao menos N eventos sem prova temporal (0 = sempre); use no cron",
    )
    markets_anchor.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    serve = subcommands.add_parser("serve", help="sobe o dashboard (localhost por padrão; --expose exige token)")
    serve.add_argument("--host", default="127.0.0.1", help="padrão 127.0.0.1 (só local)")
    serve.add_argument("--port", type=int, default=8712)
    serve.add_argument(
        "--expose",
        action="store_true",
        help="escuta em 0.0.0.0 e EXIGE THE_EYE_DASHBOARD_TOKEN (falha-fechada)",
    )
    serve.add_argument("--markets-db", type=Path, default=None)
    maxcut = subcommands.add_parser("benchmark-maxcut", help="Max-Cut 12–16 qubits: QAOA vs ótimo exato (curva QAR×p)")
    maxcut.add_argument("--nodes", type=int, default=14, help="nº de nós/qubits (par, 4–20)")
    maxcut.add_argument("--layers", default="1,2,3", help="camadas p do QAOA, ex.: 1,2,3")
    maxcut.add_argument("--grid", type=int, default=12, help="resolução da busca de ângulos")
    maxcut.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    projeto = subcommands.add_parser(
        "projeto-medir", help="mede o projeto (método declarado) e sela a medição na cadeia (hash)"
    )
    projeto.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    projeto.add_argument("--no-audit", action="store_true", help="só medir, sem selar na cadeia")
    mlops = subcommands.add_parser(
        "mlops-benchmark",
        help="roda a suíte de benchmark como corrida ML rastreada e SELADA (estilo MLflow, com prova)",
    )
    mlops.add_argument("--shots", type=int, default=1_024)
    mlops.add_argument("--layers", type=int, default=2)
    mlops.add_argument("--seed", type=int, default=42)
    mlops.add_argument("--stability-runs", type=int, default=10)
    mlops.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    mlops.add_argument("--no-audit", action="store_true", help="rastreia no store sem selar na cadeia")
    mlops_promover = subcommands.add_parser(
        "mlops-promover",
        help="promove uma versão de modelo a campeão/desafiante e sela a decisão na cadeia",
    )
    mlops_promover.add_argument("--modelo", required=True, help="modelo_id (slug)")
    mlops_promover.add_argument("--versao", required=True, help="versão do modelo (slug)")
    mlops_promover.add_argument("--papel", required=True, choices=("campeao", "desafiante"), help="papel da versão")
    mlops_promover.add_argument("--motivo", required=True, help="motivo da promoção (obrigatório)")
    mlops_promover.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    mlops_promover.add_argument("--no-audit", action="store_true", help="registra sem selar na cadeia")
    publicar_ancora = subcommands.add_parser(
        "publicar-ancora",
        help="publica lote + âncora no D1 para o verificador público servir GET /root/AAAA-MM-DD",
    )
    publicar_ancora.add_argument("--ledger-url", default=os.environ.get("THE_EYE_LEDGER_URL", ""))
    publicar_ancora.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    ledger_sync = subcommands.add_parser(
        "ledger-sync",
        help="espelha a corrente selada no ledger restrito da nuvem (D1) — idempotente por conteúdo",
    )
    ledger_sync.add_argument("--ledger-url", default=os.environ.get("THE_EYE_LEDGER_URL", ""))
    ledger_sync.add_argument("--eventos", type=Path, default=Path("reports/markets/eventos.jsonl"))
    ledger_sync.add_argument("--tenant", default=DEFAULT_TENANT)
    ledger_sync.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    verificar_espelho = subcommands.add_parser(
        "verificar-espelho",
        help="compara a corrente local com o espelho no D1 e reporta faltantes",
    )
    verificar_espelho.add_argument("--ledger-url", default=os.environ.get("THE_EYE_LEDGER_URL", ""))
    verificar_espelho.add_argument("--eventos", type=Path, default=Path("reports/markets/eventos.jsonl"))
    verificar_espelho.add_argument("--tenant", default=DEFAULT_TENANT)
    verificar_espelho.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    export_static = subcommands.add_parser(
        "export-static",
        help="renderiza os painéis do dashboard como HTML estático em dist/",
    )
    export_static.add_argument(
        "--out",
        type=Path,
        default=Path("dist"),
        help="diretório de saída (padrão: dist/)",
    )
    export_static.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    relatorio_mensal = subcommands.add_parser(
        "relatorio-mensal",
        help="gera o extrato mensal em Markdown da atividade real da plataforma",
    )
    relatorio_mensal.add_argument("--mes", default=None, help="mês de referência em AAAA-MM (padrão: mês UTC atual)")
    relatorio_mensal.add_argument("--saida", type=Path, default=None, help="arquivo Markdown de saída")
    relatorio_anual = subcommands.add_parser(
        "relatorio-anual",
        help="gera o consolidado anual em Markdown da atividade real da plataforma",
    )
    relatorio_anual.add_argument("--ano", default=None, help="ano de referência em AAAA (padrão: ano UTC atual)")
    relatorio_anual.add_argument("--saida", type=Path, default=None, help="arquivo Markdown de saída")
    doutor = subcommands.add_parser("doutor", help="diagnóstico local honesto da plataforma em um comando")
    doutor.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    return parser


def _reports_base() -> Path:
    base = Path("reports")
    if base.is_dir():
        return base
    return Path(__file__).resolve().parents[2] / "reports"


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
    if args.command == "adjudicate":
        from asus_theye.llm import DualModelError, RemoteLLMError, adjudicate

        try:
            verdict = adjudicate(
                args.question,
                proposer=args.proposer,
                challenger=args.challenger,
                proposer_model=args.proposer_model,
                challenger_model=args.challenger_model,
                temperature=args.temperature,
                ledger_url=args.ledger_url or None,
            )
        except (DualModelError, RemoteLLMError) as error:
            print(f"adjudicate: {error}")
            return 1
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        # A split verdict is a real outcome, not a crash — but it must not read
        # as success to a script that only checks the exit code.
        return 0 if verdict["claim_class"] != "CONFLICTED" else 2
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

        # As fontes descobertas vivem em disco; ler [] aqui era o motivo de a
        # cobertura aparecer 0,0% mesmo depois de a descoberta ter rodado.
        fontes_path = Path("data/source-graph/sources.json")
        fontes = []
        if fontes_path.exists():
            fontes = json.loads(fontes_path.read_text(encoding="utf-8")).get("sources", [])
        coverage = build_coverage(fontes)
        tracks = coverage_by_track(coverage)
        if fontes:
            pendentes = sum(1 for f in fontes if f.get("human_review", {}).get("status") == "pending")
            print(f"fontes carregadas: {len(fontes)} ({pendentes} aguardando revisao humana)")
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
            # len(fontes), nao 0: o literal antigo fazia a medicao ancorada
            # subnotificar para zero mesmo com fontes carregadas.
            snapshot = {
                "sources_total": len(fontes),
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
    if args.command == "markets-reconcile":
        from asus_theye.markets import MarketsSourceError, reconcile, skill_report

        try:
            report = reconcile(args.db)
            skill = skill_report(args.db, baseline_probability=args.baseline) if args.skill else None
        except MarketsSourceError as error:
            print(f"markets-reconcile: {error}")
            return 1
        if args.json_out:
            output = {**report, "skill": skill} if args.skill else report
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0 if report["tie_out"] else 1
        print("=" * 62)
        print("MERCADOS PREDITIVOS — RECONCILIAÇÃO CONTRA O BANCO MEDIDO")
        print("=" * 62)
        print(f"\nliquidados: {report['settled_total']}    tie_out: {report['tie_out']}\n")
        for area in report["areas"]:
            ok = area["aggregate_matches"] and area["per_contract_matches"]
            print(
                f"  {area['area_id']:20s} n={area['n']:3d}  "
                f"módulo={area['module_brier']}  publicado={area['published_brier']}  "
                f"[{'ok' if ok else 'DIVERGE'}]"
            )
        if skill is not None:
            fixo = f"{args.baseline}" if args.baseline is not None else "taxa-base por área"
            print(f"\nSKILL vs baseline ({fixo}):")
            for area in skill["areas"]:
                valor = "indefinida" if area["skill_score"] is None else f"{area['skill_score']:+.4f}"
                marca = "BASELINE VENCE" if area["baseline_beats_model"] else "tem skill"
                print(f"  {area['area_id']:20s} n={area['n']:3d}  skill={valor:>11s}  [{marca}]")
        # tie_out False (ou banco ausente) sai com código != 0 para um script pegar.
        return 0 if report["tie_out"] else 1
    if args.command == "markets-resolve":
        from asus_theye.markets import MarketClaimError, ResolutionError, ScoringError
        from asus_theye.markets.auditoria import (
            AuditoriaError,
            abrir_auditoria,
            cabeca_da_corrente,
            selar_liquidacao,
        )
        from asus_theye.markets.fonte_bcb import FonteBCBError, ipca_mensal
        from asus_theye.markets.fonte_ptax import ptax_venda_fim_do_mes
        from asus_theye.markets.fonte_selic import selic_meta
        from asus_theye.markets.live import LiveMarketError, resolver_pendentes
        from asus_theye.markets.sinais_ipca import probabilidade_para_ipca

        # caminhos de auditoria ancorados no --store: rodar de outro diretório
        # não pode criar uma corrente paralela em silêncio
        pasta = args.store.parent
        caminho_eventos = pasta / "eventos.jsonl"
        try:
            sdk = (
                None
                if args.no_audit
                else abrir_auditoria(
                    pasta.parent / "audit" / "markets-ledger.db",
                    caminho_chave=pasta.parent / "audit" / "pseudonimos.key",
                    eventos=caminho_eventos,
                    fingerprint=pasta / "chave.fingerprint",
                )
            )
        except AuditoriaError as error:
            print(f"markets-resolve: {error}")
            return 1
        auditor = None
        if sdk is not None:
            sdk_vivo = sdk  # variável estreitada: mypy não estreita capturas em lambda

            def auditor(linha: dict) -> dict:
                return selar_liquidacao(sdk_vivo, linha, eventos=caminho_eventos)

        try:
            acoes = resolver_pendentes(
                ipca_mensal,
                store=args.store,
                auditor=auditor,
                # M1: emissão com sinais reais por padrão; falha de sinal já
                # degrada para o prior honesto dentro do resolvedor
                gerador_de_sinais=None if args.sem_sinais else probabilidade_para_ipca,
                # M2/M3: cada área liquida contra o PRÓPRIO conector oficial
                fetchers_por_area={"juros": selic_meta, "cambio": ptax_venda_fim_do_mes},
            )
        except (FonteBCBError, LiveMarketError, MarketClaimError, ResolutionError, ScoringError) as error:
            print(f"markets-resolve: {error}")
            return 1
        houve_erro = any(acao["acao"] in ("erro", "auditoria_falhou") for acao in acoes)
        if args.json_out:
            print(json.dumps(acoes, ensure_ascii=False, indent=2))
            return 1 if houve_erro else 0
        print("=" * 62)
        print("MERCADOS — RESOLUÇÃO CONTRA A FONTE OFICIAL")
        print("=" * 62)
        if not acoes:
            print("\nregistro vazio — nada a resolver")
        for acao in acoes:
            rotulo = acao["acao"].upper()
            detalhe = ""
            if acao["acao"] == "liquidado":
                ressalva = (
                    " [p no limiar de máxima incerteza — desenho do gerador]" if acao.get("max_uncertainty") else ""
                )
                detalhe = (
                    f" desfecho={acao['outcome']} valor={acao['valor_observado']}"
                    f" brier={acao['brier_do_contrato']} fonte={acao['fonte']!r}{ressalva}"
                )
            elif acao["acao"] == "selado":
                detalhe = f" evento={acao['event_hash']}…"
            elif "motivo" in acao:
                detalhe = f" — {acao['motivo']}"
            print(f"  [{rotulo:12s}] {acao['claim_id']}{detalhe}")
        if sdk is not None:
            print(f"\ncadeia auditável: topo na sequência {cabeca_da_corrente(sdk)}")
        return 1 if houve_erro else 0
    if args.command == "markets-anchor":
        from asus_theye.audit.anchor import eventos_sem_ancora

        if getattr(args, "minimo", 0) > 0:
            lacuna = eventos_sem_ancora(args.eventos)
            if lacuna < args.minimo:
                print(f"markets-anchor: {lacuna} evento(s) sem âncora — abaixo do mínimo ({args.minimo}); nada a fazer")
                return 0
            print(f"markets-anchor: {lacuna} evento(s) sem prova temporal — ancorando")
        from asus_theye.audit.anchor import (
            RPC_PADRAO,
            AncoragemError,
            ancorar_na_base_sepolia,
            ensaiar_offline,
            lote_da_corrente,
            registrar_ancora,
        )

        try:
            batch = lote_da_corrente(args.eventos)
            manifest = batch["manifest"]
            if args.execute:
                tx_info = ancorar_na_base_sepolia(batch, executar=True, rpc=args.rpc or RPC_PADRAO)
                registrar_ancora(args.eventos.parent.parent / "audit" / "markets-ledger.db", batch, tx_info)
                resultado = {"lote": manifest, "ancora": tx_info, "registro": "gravado"}
            else:
                ensaio = ensaiar_offline(batch)
                resultado = {"lote": manifest, "ensaio": ensaio}
        except AncoragemError as error:
            print(f"markets-anchor: {error}")
            return 1
        if args.json_out:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return 0
        print("=" * 62)
        print("ANCORAGEM — LOTE MERKLE DA CORRENTE")
        print("=" * 62)
        print(f"\neventos: {manifest['event_count']} (seq {manifest['first_sequence']}–{manifest['last_sequence']})")
        print(f"merkle_root:   {manifest['merkle_root']}")
        print(f"manifest_hash: {manifest['manifest_hash_sha256']}")
        if args.execute:
            print(f"\nANCORADO na Base Sepolia (chain {resultado['ancora']['chain_id']})")
            print(f"contrato: {resultado['ancora']['contrato']}")
            print(f"tx:       {resultado['ancora']['tx_hash']}")
            print(f"bloco:    {resultado['ancora']['block_number']}")
            print("registro: audit_batches + audit_anchors + reports/markets/ancoras.jsonl")
        else:
            ensaio = resultado["ensaio"]
            print(f"\nENSAIO OFFLINE ok: contrato {ensaio['contrato']} (EVM em memória)")
            print(f"gás: deploy={ensaio['gas_deploy']}  anchor={ensaio['gas_anchor']}")
            print("\nbroadcast real: markets-anchor --execute (exige THE_EYE_ANCHOR_EXECUTE=1,")
            print("carteira fundada na Base Sepolia; mainnet é recusada por construção)")
        return 0
    if args.command == "serve":
        from asus_theye.dashboard.app import create_dashboard_app
        from asus_theye.dashboard.auth import AuthConfigError

        host = "0.0.0.0" if args.expose else args.host  # noqa: S104 - só com --expose e token
        try:
            app = create_dashboard_app(markets_db=args.markets_db, require_auth=args.expose)
        except AuthConfigError as error:
            print(f"serve: {error}")
            return 1
        alcance = "EXPOSTO (0.0.0.0, com token)" if args.expose else "local (127.0.0.1)"
        print(f"dashboard em http://{host}:{args.port}  [{alcance}]")
        try:
            import uvicorn
        except ImportError:
            print("serve: instale o extra do dashboard (pip install 'asus-the-eye[dashboard]')")
            return 1
        uvicorn.run(app, host=host, port=args.port, log_level="info")
        return 0
    if args.command == "benchmark-maxcut":
        from asus_theye.benchmark.maxcut import MaxCutError, benchmark_maxcut, grafo_3_regular

        try:
            problema = grafo_3_regular(args.nodes)
            ps = tuple(int(x) for x in str(args.layers).split(","))
            relatorio = benchmark_maxcut(problema, ps=ps, grid=args.grid)
        except (MaxCutError, ValueError) as error:
            print(f"benchmark-maxcut: {error}")
            return 1
        if args.json_out:
            print(json.dumps(relatorio, ensure_ascii=False, indent=2))
            return 0
        print("=" * 62)
        print(f"MAX-CUT — {relatorio['n_qubits']} QUBITS (QAOA local × ótimo exato)")
        print("=" * 62)
        print(f"\nótimo clássico EXATO (força bruta 2^N): {relatorio['otimo_classico_exato']}")
        print("\ncurva QAR × p:")
        for pt in relatorio["curva_qar_por_p"]:
            print(
                f"  p={pt['p']}  ⟨corte⟩={pt['expected_cut']:.3f}  "
                f"QAR={pt['qar']:.4f}  mais_provável={pt['most_probable_cut']}"
            )
        print(f"\nressalva: {relatorio['ressalva']}")
        return 0
    if args.command == "projeto-medir":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria, cabeca_da_corrente
        from asus_theye.projeto import MedicaoError, medir_projeto, selar_projeto

        try:
            snap = medir_projeto()
        except MedicaoError as error:
            print(f"projeto-medir: {error}")
            return 1
        recibo = None
        sdk = None
        if not args.no_audit:
            try:
                sdk = abrir_auditoria()
                recibo = selar_projeto(sdk, snap)
            except AuditoriaError as error:
                print(f"projeto-medir: {error}")
                return 1
        if args.json_out:
            print(json.dumps({"medicao": snap, "selagem": recibo}, ensure_ascii=False, indent=2))
            return 0
        caminho = snap["caminho_minimo"]
        print("=" * 62)
        print("MEDIÇÃO DO PROJETO — sempre em hash")
        print("=" * 62)
        print(f"\ncaminho mínimo: {caminho['pct']}%  ({caminho['metodo']})")
        for fase in caminho["fases"]:
            print(f"  {fase['id']}  {float(fase['peso_concluido']) * 100:5.0f}%  {fase['estado']:9s}  {fase['nome']}")
        produtos = snap["produtos"]
        if produtos["fases"]:
            print(f"\nroteiro dos produtos: {produtos['pct']}%  (checklist vivo — {len(produtos['fases'])} fases)")
            for fase in produtos["fases"]:
                print(
                    f"  {fase['id']:3s}  {float(fase['peso_concluido']) * 100:5.0f}%  "
                    f"{fase['estado']:9s}  {fase['nome']}"
                )
        corrente = snap["corrente"]
        print(f"\ncorrente: {corrente['eventos']} eventos  verifica={corrente['verifica']}")
        print(
            f"medição contínua: {snap['medicao_continua']['liquidados']} liquidados, "
            f"{snap['medicao_continua']['resolucoes']} resoluções | âncoras: {snap['ancoragem']['ancoras']}"
        )
        print(f"\nhash da medição: {snap['hash_da_medicao']}")
        if recibo is not None and sdk is not None:
            estado = "dedupe (estado inalterado)" if recibo.get("duplicate") else "EVENTO NOVO selado"
            print(f"selagem: {estado} — cadeia no topo {cabeca_da_corrente(sdk)}")
        print(f"\n{snap['ressalva']}")
        return 0
    if args.command == "mlops-benchmark":
        from asus_theye.audit.schema import EventValidationError
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.mlops import MLOpsError, registrar_corrida, registrar_modelo, registrar_versao
        from asus_theye.mlops.producers import MODELO_BENCHMARK, corrida_do_benchmark, versao_do_benchmark

        sdk_ml = None
        if not args.no_audit:
            try:
                sdk_ml = abrir_auditoria()
            except AuditoriaError as error:
                print(f"mlops-benchmark: {error}")
                return 1
        report, path = run_benchmark_suite(
            shots=args.shots, layers=args.layers, seed=args.seed, stability_runs=args.stability_runs
        )
        try:
            registrar_modelo(MODELO_BENCHMARK, sdk=sdk_ml)
            registrar_versao(versao_do_benchmark(), sdk=sdk_ml)
            resultado = registrar_corrida(
                corrida_do_benchmark(
                    report,
                    path,
                    shots=args.shots,
                    layers=args.layers,
                    seed=args.seed,
                    stability_runs=args.stability_runs,
                ),
                sdk=sdk_ml,
            )
        except (MLOpsError, AuditoriaError, EventValidationError) as error:
            print(f"mlops-benchmark: {error}")
            return 1
        if args.json_out:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return 0
        corrida = resultado["registro"]
        print("=" * 62)
        print("CORRIDA ML RASTREADA — estilo MLflow, com prova")
        print("=" * 62)
        print(f"\nmodelo: {corrida['modelo_id']}@{corrida['versao']}")
        for nome, valor in corrida["metricas"].items():
            print(f"  {nome}: {valor}")
        print(f"\ncorrida_id: {corrida['corrida_id']}")
        print(f"artefato: {corrida['artefatos'][0]['caminho']} (sha256 {corrida['artefatos'][0]['sha256'][:16]}…)")
        if resultado["duplicate"]:
            print("\nstore: dedupe — corrida byte-idêntica já rastreada")
        else:
            print("\nstore: corrida NOVA em reports/mlops/corridas.jsonl")
        if resultado["selagem"] is not None:
            selagem = resultado["selagem"]
            estado_selo = "dedupe na cadeia" if selagem.get("duplicate") else "EVENTO ml.run SELADO"
            print(f"selagem: {estado_selo} — event_hash {selagem['event_hash_sha256'][:16]}…")
        return 0
    if args.command == "markets-emitir":
        from asus_theye.markets.live import (
            LiveMarketError,
            carregar_registro,
            emitir_area,
            salvar_registro,
        )

        try:
            registro = carregar_registro(args.store)
            mercado_novo = emitir_area(registro, args.area, args.mes, limiar=args.limiar)
            if mercado_novo is None:
                print(f"markets-emitir: {args.area}/{args.mes} já tem mercado — nada a emitir")
                return 0
            salvar_registro(args.store, registro)
        except LiveMarketError as error:
            print(f"markets-emitir: {error}")
            return 1
        if args.json_out:
            print(json.dumps(mercado_novo, ensure_ascii=False, indent=2))
            return 0
        print("=" * 62)
        print("MERCADO EMITIDO")
        print("=" * 62)
        print(f"\n{mercado_novo['claim_id']}  (p = {mercado_novo['probability']:.2f}, prior honesto)")
        print(f"{mercado_novo['question']}")
        print(f"critério: {mercado_novo['criterio']}  |  fonte: {mercado_novo['resolution_source']}")
        return 0
    if args.command == "markets-vintage":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.markets.vintage_focus import VintageError, arquivar_vintage

        try:
            sdk_v = None if args.no_audit else abrir_auditoria()
            resultado = arquivar_vintage(args.mes, sdk=sdk_v)
        except (VintageError, AuditoriaError) as error:
            print(f"markets-vintage: {error}")
            return 1
        if args.json_out:
            print(json.dumps(resultado["registro"], ensure_ascii=False, indent=2))
            return 0
        reg = resultado["registro"]
        print("=" * 62)
        print("VINTAGE DO FOCUS — o consenso como ele era hoje")
        print("=" * 62)
        if reg is None:
            print(f"\n{args.mes}: {resultado['motivo']} — nada a arquivar (UNKNOWN, não zero)")
            return 0
        print(f"\nmês {reg['mes_referencia']} | mediana {reg['mediana']:.2f}% | boletim {reg['data_do_boletim']}")
        print(f"fonte: {reg['fonte']}")
        print(f"vintage_id: {reg['vintage_id'][:32]}…")
        if resultado["duplicate"]:
            print("\n(mesmo boletim já arquivado — dedupe)")
        if resultado["selagem"] is not None:
            s = resultado["selagem"]
            estado_selo = "dedupe" if s.get("duplicate") else "EVENTO market.vintage SELADO"
            print(f"selagem: {estado_selo} — {s['event_hash_sha256'][:16]}…")
        return 0
    if args.command == "markets-comparar":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.markets.comparador import ComparadorError, observar_divergencia
        from asus_theye.markets.fonte_kalshi import FonteKalshiError, preco_kalshi
        from asus_theye.markets.resolution import ResolutionError

        try:
            preco = args.preco
            if preco is None:  # busca AO VIVO na API pública (só leitura, sem chave)
                observado = preco_kalshi(args.ticker)
                if observado is None:
                    print(f"markets-comparar: ticker {args.ticker!r} não existe na Kalshi")
                    return 1
                if observado.status != "active":
                    print(
                        f"markets-comparar: mercado {args.ticker} está {observado.status!r} — "
                        "preço fora de negociação não é observação de comparador"
                    )
                    return 1
                preco = observado.probabilidade_implicita
                print(f"preço ao vivo ({observado.metodo_do_preco}): {preco:.4f} — {observado.title}")
            sdk_comparar = None if args.no_audit else abrir_auditoria(Path("reports/audit/markets-ledger.db"))
            resultado = observar_divergencia(
                claim_id=args.claim,
                comparator_price=preco,
                ticker=args.ticker,
                nota_de_mapeamento=args.nota,
                sdk=sdk_comparar,
            )
        except (ComparadorError, ResolutionError, AuditoriaError, FonteKalshiError) as error:
            print(f"markets-comparar: {error}")
            return 1
        if args.json_out:
            print(
                json.dumps(resultado["registro"] | {"duplicate": resultado["duplicate"]}, ensure_ascii=False, indent=2)
            )
            return 0
        registro = resultado["registro"]
        print("=" * 62)
        print("DIVERGÊNCIA VS COMPARADOR — medida, nunca resolutora")
        print("=" * 62)
        print(f"\nclaim: {registro['claim_id']}  |  ticker: {registro['ticker']}")
        print(f"nossa probabilidade: {registro['our_probability']:.4f}")
        print(f"preço {registro['comparator']}: {registro['comparator_price']:.4f}")
        print(f"divergência: {registro['divergence']:.4f}")
        print(f"\nmapeamento: {registro['nota_de_mapeamento']}")
        print(f"{registro['note']}")
        if resultado["duplicate"]:
            print("\n(observação idêntica já registrada — dedupe)")
        if resultado["selagem"] is not None:
            selo = resultado["selagem"]
            estado_selo = "dedupe na cadeia" if selo.get("duplicate") else "EVENTO market.comparator SELADO"
            print(f"selagem: {estado_selo} — event_hash {selo['event_hash_sha256'][:16]}…")
        return 0
    if args.command == "markets-sinais":
        from asus_theye.markets.gerador import GeradorError
        from asus_theye.markets.sinais_ipca import SinaisError, probabilidade_para_ipca, sinais_para_ipca

        try:
            sinais = sinais_para_ipca(args.mes, args.limiar)
            prob = probabilidade_para_ipca(args.mes, args.limiar)
        except (SinaisError, GeradorError) as error:
            print(f"markets-sinais: {error}")
            return 1
        if args.json_out:
            print(
                json.dumps(
                    {
                        "mes": args.mes,
                        "limiar": args.limiar,
                        "sinais": [{"direcao": s.direcao, "peso": s.peso, "fonte": s.fonte} for s in sinais],
                        "probabilidade": prob.as_dict(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        print("=" * 62)
        print(f"SINAIS REAIS — IPCA {args.mes} >= {args.limiar:.2f}%?")
        print("=" * 62)
        if not sinais:
            print("\nnenhuma fonte publicou ainda — sem sinal, sem convicção (p = 0,50)")
        for sinal in sinais:
            print(f"\n[{sinal.direcao.upper():3s}] peso {sinal.peso:.0f} — {sinal.fonte}")
        print(f"\nprobabilidade WPAM: {prob.valor:.4f}  (prior {prob.p_inicial} × {prob.peso_inicial:.0f})")
        print(f"max_uncertainty: {prob.max_uncertainty}")
        return 0
    if args.command == "publicar-ancora":
        from asus_theye.audit.anchor import AncoragemError
        from asus_theye.audit.publicar_ancora import PublicacaoError, publicar

        if not args.ledger_url:
            print("publicar-ancora: exige --ledger-url ou THE_EYE_LEDGER_URL")
            return 1
        try:
            resultado = publicar(args.ledger_url)
        except (PublicacaoError, AncoragemError) as error:
            print(f"publicar-ancora: {error}")
            return 1
        if args.json_out:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return 0
        print("=" * 62)
        print("RAIZ PUBLICADA NO VERIFICADOR (D1)")
        print("=" * 62)
        print(f"\nmerkle_root: {resultado['merkle_root']}")
        print(f"tx on-chain: {resultado['tx_hash']}")
        print(f"lote:   {json.dumps(resultado['lote'], ensure_ascii=False)}")
        print(f"ancora: {json.dumps(resultado['ancora'], ensure_ascii=False)}")
        print(f"\n{resultado['metodo']}")
        return 0
    if args.command == "ledger-sync":
        from asus_theye.audit.remote_ledger import LedgerPublishError
        from asus_theye.audit.sync_ledger import SyncError, sincronizar

        if not args.ledger_url:
            print("ledger-sync: exige --ledger-url ou THE_EYE_LEDGER_URL")
            return 1
        try:
            placar = sincronizar(args.ledger_url, eventos=args.eventos, tenant=args.tenant)
        except (SyncError, LedgerPublishError) as error:
            print(f"ledger-sync: {error}")
            return 1
        if args.json_out:
            print(json.dumps(placar, ensure_ascii=False, indent=2))
            return 0
        print("=" * 62)
        print("ESPELHO DA CORRENTE NA NUVEM (D1)")
        print("=" * 62)
        print(
            f"\neventos locais: {placar['eventos_locais']}  |  novos: {placar['novos']}  |  dedupe: {placar['dedupe']}"
        )
        print(f"\n{placar['metodo']}")
        return 0
    if args.command == "verificar-espelho":
        from asus_theye.audit.verificar_espelho import (
            CorrenteBrokenError,
            VerificarEspelhoError,
            verificar,
        )

        if not args.ledger_url:
            print("verificar-espelho: exige --ledger-url ou THE_EYE_LEDGER_URL")
            return 1
        try:
            relatorio = verificar(args.ledger_url, eventos=args.eventos, tenant=args.tenant)
        except (CorrenteBrokenError, VerificarEspelhoError, FileNotFoundError) as error:
            print(f"verificar-espelho: {error}")
            return 1
        if args.json_out:
            print(json.dumps(relatorio, ensure_ascii=False, indent=2))
            ok = relatorio["cobertura_da_janela"] and not relatorio["faltantes_na_janela"]
            return 0 if ok else 1
        print("=" * 62)
        print("VERIFICAÇÃO DO ESPELHO DA CORRENTE (D1)")
        print("=" * 62)
        print(f"\nlocais: {relatorio['locais']}  |  espelhos_remotos: {relatorio['espelhos_remotos']}")
        if relatorio["janela_parcial"]:
            print("\nATENÇÃO: corrente local > 50 eventos — janela parcial (últimos 50 visíveis)")
        if not relatorio["matching_por_hash"]:
            print("\nmatching por hash indisponível (o GET do worker não devolve idempotency_key);")
            print(f"cobertura por contagem da janela: {'OK' if relatorio['cobertura_da_janela'] else 'INCOMPLETA'}")
        if relatorio["faltantes_na_janela"]:
            print(f"\nFALTANTES na janela ({len(relatorio['faltantes_na_janela'])}):")
            for h in relatorio["faltantes_na_janela"]:
                print(f"  {h}")
            return 1
        if not relatorio["cobertura_da_janela"]:
            print("\ncobertura da janela INCOMPLETA — rode asus-theye ledger-sync")
            return 1
        print("\nespelho em dia — nenhum faltante na janela")
        return 0
    if args.command == "doutor":
        from asus_theye.diagnostico import diagnosticar

        relatorio = diagnosticar(_reports_base())
        falhou_critico = any(not bool(relatorio[chave]["ok"]) for chave in ("corrente", "chave"))
        if args.json_out:
            print(json.dumps(relatorio, ensure_ascii=False, indent=2))
            return 1 if falhou_critico else 0
        titulos = {
            "corrente": "corrente",
            "chave": "chave",
            "prova_temporal": "prova temporal",
            "mercados": "mercados",
            "espelho": "espelho",
            "titularidade": "titularidade",
            "backup": "backup",
        }
        print("=" * 62)
        print("DOUTOR — DIAGNÓSTICO HONESTO DA PLATAFORMA")
        print("=" * 62)
        for chave, titulo in titulos.items():
            item = relatorio[chave]
            if item["ok"]:
                marcador = "OK"
            elif chave in {"corrente", "chave"}:
                marcador = "CRÍTICO"
            else:
                marcador = "AVISO"
            print(f"\n[{marcador:7s}] {titulo}")
            print(f"  {item['detalhe']}")
            if not item["ok"]:
                print(f"  como corrigir: {item['como_corrigir']}")
        return 1 if falhou_critico else 0
    if args.command == "relatorio-mensal":
        from asus_theye.relatorio import relatorio_mensal

        try:
            texto = relatorio_mensal(args.mes, base=_reports_base())
        except ValueError as error:
            print(f"relatorio-mensal: {error}")
            return 1
        if args.saida is not None:
            args.saida.parent.mkdir(parents=True, exist_ok=True)
            args.saida.write_text(texto, encoding="utf-8")
            print(f"relatório: {args.saida}")
            return 0
        print(texto)
        return 0
    if args.command == "relatorio-anual":
        from asus_theye.relatorio import relatorio_anual

        try:
            texto = relatorio_anual(args.ano, base=_reports_base())
        except ValueError as error:
            print(f"relatorio-anual: {error}")
            return 1
        if args.saida is not None:
            args.saida.parent.mkdir(parents=True, exist_ok=True)
            args.saida.write_text(texto, encoding="utf-8")
            print(f"relatório: {args.saida}")
            return 0
        print(texto)
        return 0
    if args.command == "export-static":
        from asus_theye.dashboard.export_static import exportar

        resultado = exportar(args.out)
        if args.json_out:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return 0
        print("=" * 62)
        print("EXPORT ESTÁTICO DOS PAINÉIS DO DASHBOARD")
        print("=" * 62)
        for nome in resultado["gerados"]:
            print(f"  gerado: {args.out / nome}")
        for motivo in resultado["pulados"]:
            print(f"  pulado: {motivo}")
        return 0
    if args.command == "mlops-promover":
        from asus_theye.audit.schema import EventValidationError
        from asus_theye.audit.sdk import utc_now
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.mlops import MLOpsError, campeao_atual, promover

        sdk_ml = None
        if not args.no_audit:
            try:
                sdk_ml = abrir_auditoria()
            except AuditoriaError as error:
                print(f"mlops-promover: {error}")
                return 1
        try:
            resultado = promover(
                modelo_id=args.modelo,
                versao=args.versao,
                papel=args.papel,
                motivo=args.motivo,
                promovido_em=utc_now(),
                sdk=sdk_ml,
            )
        except (MLOpsError, AuditoriaError, EventValidationError) as error:
            print(f"mlops-promover: {error}")
            return 1
        campiao = campeao_atual(args.modelo)
        if args.json_out:
            print(json.dumps({"resultado": resultado, "campeao_atual": campiao}, ensure_ascii=False, indent=2))
            return 0
        reg = resultado["registro"]
        print(f"papel: {reg['papel']}")
        print(f"modelo: {reg['modelo_id']}@{reg['versao']}")
        print(f"motivo: {reg['motivo']}")
        if campiao:
            print(f"campeao atual: {campiao['modelo_id']}@{campiao['versao']} (promovido_em {campiao['promovido_em']})")
        else:
            print("campeao atual: nenhum")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
