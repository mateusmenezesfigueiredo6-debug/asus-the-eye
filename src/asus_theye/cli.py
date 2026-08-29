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
    markets_emitir.add_argument(
        "--sem-gerador",
        action="store_true",
        help="emite no prior 0,50 sem consultar sinais (o padrão É consultar — mercado que nasce "
        "em cara-ou-coroa por omissão não é previsão)",
    )
    markets_emitir.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_reprecificar = subcommands.add_parser(
        "markets-reprecificar",
        help="move p de um mercado ABERTO com a proveniência do sinal e sela a mudança",
    )
    markets_reprecificar.add_argument("--claim", required=True, help="claim_id do mercado aberto")
    markets_reprecificar.add_argument(
        "--motivo", default="sinal novo disponível na fonte", help="por que o preço mudou"
    )
    markets_reprecificar.add_argument("--store", type=Path, default=Path("reports/markets/registro.json"))
    markets_reprecificar.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_reprecificar.add_argument("--no-audit", action="store_true", help="não selar na cadeia")
    markets_rodada = subcommands.add_parser(
        "markets-rodada",
        help="laço diário: consulta o gerador de cada mercado ABERTO e reprecifica o que mudou",
    )
    markets_rodada.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_rodada.add_argument("--no-audit", action="store_true", help="não selar na cadeia")
    projeto_fronteira = subcommands.add_parser(
        "projeto-fronteira",
        help="verifica e SELA que a titularidade, a proveniência e a fronteira de terceiros seguem intactas",
    )
    projeto_fronteira.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    projeto_fronteira.add_argument("--no-audit", action="store_true", help="só verificar, sem selar")
    markets_vintage = subcommands.add_parser(
        "markets-vintage",
        help="arquiva o consenso Focus vigente (vintage) e sela — destrava o Brier comparativo do nowcast",
    )
    markets_vintage.add_argument("--mes", required=True, help="mês de referência, aaaa-mm")
    markets_vintage.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_vintage.add_argument("--no-audit", action="store_true", help="arquiva sem selar na cadeia")
    markets_nowcast = subcommands.add_parser(
        "markets-nowcast",
        help="executa o nowcast desafiante do IPCA (ridge walk-forward) e grava manifesto em reports/mlops/",
    )
    markets_nowcast.add_argument(
        "--spec",
        dest="especificacao",
        default="R2",
        choices=["R2", "R4"],
        help="especificação de features: R2 (IPCA-15+IGP-M) ou R4 (+ dólar + Selic); padrão: R2",
    )
    markets_nowcast.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
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
    markets_comparar.add_argument(
        "--comparador",
        default="Kalshi",
        help="nome verdadeiro do comparador no store (ex.: 'Focus/BCB' para o consenso público)",
    )
    markets_comparar.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_comparar.add_argument("--no-audit", action="store_true", help="não selar na cadeia")
    markets_serie = subcommands.add_parser(
        "markets-serie",
        help="grava e sela um ponto da série p(t) — a trajetória, sem a qual não há Brier por horizonte",
    )
    markets_serie.add_argument(
        "--claim", default=None, help="claim_id específico; omitido = todos os claims vivos (uso do cron)"
    )
    markets_serie.add_argument("--dia", default=None, help="data da observação (YYYY-MM-DD); padrão = hoje em UTC")
    markets_serie.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_serie.add_argument("--no-audit", action="store_true", help="não selar na cadeia")
    markets_consenso = subcommands.add_parser(
        "markets-consenso",
        help="mede o erro do consenso Focus contra o realizado — a linha de base da calibração",
    )
    markets_consenso.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_consenso.add_argument("--no-audit", action="store_true", help="não selar na cadeia")
    markets_calibracao = subcommands.add_parser(
        "markets-calibracao",
        help="mede a calibração (curva, Brier por horizonte e por área) — recusa agregar sem amostra",
    )
    markets_calibracao.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
    markets_calibracao.add_argument("--no-audit", action="store_true", help="não selar na cadeia")
    markets_global = subcommands.add_parser(
        "markets-global",
        help="consulta indicador macro de QUALQUER país na fonte global CC-BY (Banco Mundial)",
    )
    markets_global.add_argument("--pais", required=True, help="código ISO-3 (ex.: BRA, USA, JPN, DEU)")
    markets_global.add_argument("--ano", required=True, help="ano de referência (AAAA)")
    markets_global.add_argument(
        "--indicador", default="FP.CPI.TOTL.ZG", help="indicador registrado (padrão: inflação anual)"
    )
    markets_global.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
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
    carteira = subcommands.add_parser(
        "carteira",
        help="seleção quântica de carteira: QAOA escolhe QUAIS previsões publicar (vs ótimo exato)",
    )
    carteira.add_argument(
        "--real",
        action="store_true",
        help="usa os mercados ABERTOS do registro (edge só com comparador; senão convicção |2p−1| declarada)",
    )
    carteira.add_argument("--k", type=int, default=None, help="quantas previsões escolher (padrão: 3; com --real: 2)")
    carteira.add_argument("--lam", type=float, default=1.2, help="peso do risco de correlação")
    carteira.add_argument("--pen", type=float, default=3.0, help="força da regra 'exatamente K'")
    carteira.add_argument("--shots", type=int, default=2_048)
    carteira.add_argument("--layers", type=int, default=2)
    carteira.add_argument("--seed", type=int, default=7)
    carteira.add_argument("--output-dir", type=Path, default=Path("reports/benchmark"))
    carteira.add_argument(
        "--execute",
        action="store_true",
        help="roda também na QPU real (exige THE_EYE_IBM_EXECUTE=1; usa cota do Open Plan)",
    )
    carteira.add_argument("--backend", default=None, help="QPU específica (padrão: menor fila)")
    carteira.add_argument("--json", dest="json_out", action="store_true", help="saída em JSON")
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
    export_static.add_argument(
        "--publico",
        action="store_true",
        help="bundle de lançamento: exclui a telemetria interna (projeto/mlops/benchmark)",
    )
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


def _e_loopback(host: str) -> bool:
    """O host é seguramente local? Só então a app pode subir sem token.

    Loopback verdadeiro (127.0.0.0/8, ::1, localhost) é local. Qualquer outra
    coisa — 0.0.0.0, um IP de LAN, um nome — alcança a rede e exige token.
    Fail-closed: o que não sei classificar como loopback conta como exposto.
    """
    import ipaddress

    alvo = (host or "").strip().lower()
    if alvo in ("localhost", "::1", ""):
        return alvo != ""
    try:
        return ipaddress.ip_address(alvo).is_loopback
    except ValueError:
        return False  # nome não-localhost: trate como rede


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
        # As fontes descobertas vivem em disco; ler [] aqui era o motivo de a
        # cobertura aparecer 0,0% mesmo depois de a descoberta ter rodado.
        #
        # O resolvedor é o MESMO que `asus-theye chart` usa. Antes este ponto
        # lia só do diretório de trabalho e o chart lia só do pacote, então os
        # dois comandos imprimiam coberturas diferentes — e as duas eram
        # hasheadas e seladas sem dizer de qual árvore vieram.
        from asus_theye._pkg_paths import dado_vivo_ou_empacotado
        from asus_theye.audit.remote_ledger import publish_event
        from asus_theye.source_graph import (
            build_coverage,
            coverage_by_track,
            graph_built_event,
            write_reports,
        )

        fontes_path, origem_das_fontes = dado_vivo_ou_empacotado("data", "source-graph", "sources.json")
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
            # Sem `output_dir`: o default de `write_reports` já é
            # `Path.cwd()/"reports"`, avaliado tarde e correto.
            #
            # Passar `_reports_base()` aqui ANULAVA essa correção — o fallback
            # dela é `parents[2]/reports`, que instalado resolve para dentro de
            # `<venv>/lib/pythonX.Y/reports`, ou levanta PermissionError cru em
            # instalação de sistema. `_reports_base()` continua valendo nos três
            # consumidores SÓ-LEITURA (doutor, relatorio-mensal, relatorio-anual);
            # o que não pode é guiar ESCRITA.
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
                # De qual árvore vieram as fontes. Sem isto, dois snapshots de
                # safras diferentes ficam indistinguíveis dentro da corrente.
                "sources_origin": origem_das_fontes,
            }
            receipt = publish_event(graph_built_event(snapshot, commit="", tenant_id=args.tenant), args.ledger_url)
            print(f"\nLedger: sequência {receipt['sequence']}")
        return 0
    if args.command == "chart":
        from asus_theye.audit.remote_ledger import publish_event
        from asus_theye.chart import build_chart, chart_snapshot_hash, render_html, render_text
        from asus_theye.chart.builder import _REPO_ROOT, SEM_ARVORE

        # A recusa vem ANTES de qualquer chamada de rede: se o painel não pode
        # ser medido, buscar eventos no ledger é trabalho jogado fora, e uma
        # falha de rede mascararia a razão de verdade da recusa.
        if args.publish and _REPO_ROOT is None:
            print(f"chart: --publish RECUSADO — {SEM_ARVORE}")
            print("chart: rode a partir da árvore de código para publicar.")
            return 1

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
            # Selar um painel não medido é o pior desfecho possível deste
            # comando: o snapshot mistura número falso com número verdadeiro
            # (a cobertura por nicho vem do dado empacotado e continua certa),
            # e depois de selado fica na corrente para sempre. Recusar é a
            # única saída — e com código != 0, para que um cron perceba.
            # Redundante com a trava do topo, e mantida: esta lê o SNAPSHOT,
            # que é o que efetivamente vai ser selado. Se um dia a medição
            # passar a falhar por outro motivo, é aqui que se pega.
            if not snapshot.get("medivel", True):
                print(f"chart: --publish RECUSADO — {snapshot['medicao_impossivel']}")
                return 1
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
        from functools import partial

        from asus_theye.markets.fonte_bcb import FonteBCBError, ipca_mensal
        from asus_theye.markets.fonte_ptax import ptax_venda_do_dia, ptax_venda_fim_do_mes
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
                fetchers_por_area={
                    "juros": selic_meta,
                    "cambio": ptax_venda_fim_do_mes,
                    # M6: PTAX do dia — mercado diário liquida contra a cotação daquele dia
                    "cambio-diario": ptax_venda_do_dia,
                    # M5: series SGS mensais liquidam pelo MESMO conector oficial,
                    # cada uma amarrada a sua propria serie do registry
                    "ipca15": partial(ipca_mensal, serie=7478),
                    "inpc": partial(ipca_mensal, serie=188),
                    "igpm": partial(ipca_mensal, serie=189),
                    "atividade": partial(ipca_mensal, serie=24363),
                },
                # a varredura de selagem consulta o MESMO export que o auditor
                # escreve — sem isto, reconciliações registradas ficariam invisíveis
                eventos=caminho_eventos,
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

        # O host efetivo — e a auth deriva DELE, não da flag. Antes, --host
        # 0.0.0.0 sem --expose subia na rede sem token: a garantia fail-closed
        # cobria só o caminho --expose, e o outro ficava fail-OPEN. Qualquer
        # host que não seja loopback é rede, e rede exige token.
        host = "0.0.0.0" if args.expose else args.host  # noqa: S104 - exposição exige token, ver _e_loopback
        exposto = not _e_loopback(host)
        try:
            app = create_dashboard_app(markets_db=args.markets_db, require_auth=exposto)
        except AuthConfigError as error:
            print(f"serve: {error}")
            return 1
        alcance = f"EXPOSTO ({host}, com token)" if exposto else f"local ({host})"
        print(f"dashboard em http://{host}:{args.port}  [{alcance}]")
        try:
            import uvicorn
        except ImportError:
            print("serve: instale o extra do dashboard (pip install 'asus-the-eye[dashboard]')")
            return 1
        uvicorn.run(app, host=host, port=args.port, log_level="info")
        return 0
    if args.command == "carteira":
        from asus_theye.audit import AuditLedger as _LedgerCarteira
        from asus_theye.benchmark.selecao_carteira import candidatos_demo, selecionar_carteira

        diagnostico = None
        try:
            if args.real:
                from asus_theye.benchmark.selecao_real import carregar_candidatos_reais

                candidatos, correlacao, diagnostico = carregar_candidatos_reais()
            else:
                candidatos, correlacao = candidatos_demo()
            k = args.k if args.k is not None else (2 if args.real else 3)
            resultado = selecionar_carteira(
                candidatos,
                correlacao=correlacao,
                k=k,
                lam=args.lam,
                pen=args.pen,
                layers=args.layers,
                shots=args.shots,
                seed=args.seed,
                ledger=_LedgerCarteira(args.output_dir / "ledger.jsonl"),
            )
        except (ValueError, OSError, json.JSONDecodeError) as error:
            print(f"carteira: {error}")
            return 1
        if diagnostico:
            resultado = {**resultado, "real": diagnostico}
            _LedgerCarteira(args.output_dir / "ledger.jsonl").append(
                "benchmark.selecao_carteira.contexto_real", diagnostico
            )
        if args.execute:
            from asus_theye.benchmark.ibm_backend import (
                HardwareGateClosed,
                QuantumDepsMissing,
                run_selecao_on_hardware,
            )
            from asus_theye.benchmark.selecao_carteira import construir_qubo

            try:
                qubo = construir_qubo(candidatos, correlacao, resultado["k"], args.lam, args.pen)
                hw = run_selecao_on_hardware(
                    qubo,
                    len(candidatos),
                    resultado["k"],
                    layers=args.layers,
                    shots=args.shots,
                    backend_name=args.backend,
                )
            except (HardwareGateClosed, QuantumDepsMissing) as error:
                print(f"carteira: {error}")
                return 1
            codigos_hw = [c.codigo for c in candidatos]
            hw["selecao"] = [codigos_hw[i] for i, bit in enumerate(hw["solution"] or []) if bit]
            hw["bate_otimo_local"] = sorted(hw["selecao"]) == sorted(resultado["selecao_otima"])
            resultado = {**resultado, "hardware": hw}
            _LedgerCarteira(args.output_dir / "ledger.jsonl").append(
                "benchmark.selecao_carteira.hardware", hw
            )
        if args.json_out:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return 0
        print("=" * 62)
        titulo_modo = f"mercados REAIS · modo {diagnostico['modo']}" if diagnostico else "demo recuperada"
        print(f"SELEÇÃO QUÂNTICA DE CARTEIRA ({titulo_modo})")
        print("=" * 62)
        rotulo = {c.codigo: c for c in candidatos}
        for codigo in resultado["selecao"]:
            cand = rotulo[codigo]
            print(f"  [{codigo}] valor={cand.edge:+.3f}  {cand.descricao}")
        print(f"\n  valor total: {resultado['edge_total']:+.3f}  (K={resultado['k']})")
        print(f"  bate o ótimo exato? {resultado['bate_otimo']}")
        if diagnostico:
            for limitacao in diagnostico["limitacoes"]:
                print(f"  ⚠ {limitacao}")
        hardware = resultado.get("hardware")
        if hardware:
            print(f"\n  QPU REAL: {hardware['backend']}  job={hardware['job_id']}")
            print(f"  carteira do hardware: {hardware['selecao']}  (reparo K: {hardware['reparo_com_k']})")
            print(f"  hardware bate o ótimo local? {hardware['bate_otimo_local']}")
        print(f"  selado em: {args.output_dir / 'ledger.jsonl'}")
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
            # O padrão é CONSULTAR o gerador. Emitir em 0,50 por omissão foi
            # exatamente o que deixou 4 mercados em cara-ou-coroa com o motor
            # funcionando ao lado: o gerador dava 0,1667 e ninguém perguntava.
            probabilidade = None
            if not args.sem_gerador:
                from asus_theye.markets.gerador import GeradorError
                from asus_theye.markets.sinais_cambio import SinaisCambioError
                from asus_theye.markets.sinais_ipca import SinaisError
                from asus_theye.markets.sinais_juros import SinaisJurosError

                try:
                    if args.area == "juros":
                        from asus_theye.markets.sinais_juros import probabilidade_para_juros

                        probabilidade = probabilidade_para_juros(args.mes, args.limiar)
                    elif args.area == "cambio":
                        from asus_theye.markets.sinais_cambio import probabilidade_para_cambio

                        probabilidade = probabilidade_para_cambio(args.mes, args.limiar)
                    else:
                        from asus_theye.markets.sinais_ipca import probabilidade_para_ipca

                        probabilidade = probabilidade_para_ipca(args.mes, args.limiar)
                    print(f"gerador: p={probabilidade.valor:.4f} (area={args.area})")
                except (GeradorError, SinaisError, SinaisJurosError, SinaisCambioError) as erro:
                    # falha de sinal NUNCA bloqueia a emissão — o mercado nasce
                    # no prior honesto e a saída diz por quê
                    print(f"gerador indisponível ({erro}) — emitindo no prior 0,50, declarado")
            mercado_novo = emitir_area(registro, args.area, args.mes, limiar=args.limiar, probabilidade=probabilidade)
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
    if args.command == "markets-nowcast":
        from asus_theye.markets.nowcast import NowcastError, corrida_do_nowcast

        try:
            corrida = corrida_do_nowcast(args.especificacao)
        except NowcastError as error:
            print(f"markets-nowcast: {error}")
            return 1
        manifesto_path = corrida.artefatos[0]["caminho"] if corrida.artefatos else "—"
        if args.json_out:
            print(
                json.dumps(
                    {
                        "especificacao": args.especificacao,
                        "manifesto": manifesto_path,
                        "sha256": corrida.artefatos[0]["sha256"] if corrida.artefatos else None,
                        "params": corrida.params,
                        "metricas": corrida.metricas,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        print("=" * 62)
        print(f"NOWCAST IPCA — especificação {args.especificacao}")
        print("=" * 62)
        print(f"\nmanifesto: {manifesto_path}")
        brier = corrida.params.get("brier_ridge", "—")
        n = corrida.params.get("n_meses", "—")
        print(f"Brier ridge: {brier}  |  meses avaliados: {n}")
        print("\n(o desafiante permanece com peso zero até cumprir a porta prospectiva da spec)")
        return 0
    if args.command == "markets-comparar":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.markets.comparador import ComparadorError, observar_divergencia
        from asus_theye.markets.resolution import ResolutionError

        try:
            # A busca AO VIVO foi removida junto com o conector da Kalshi: os
            # termos dela restringem armazenar, compilar e exibir o dado, e este
            # produto faz as três coisas. O preço agora é informado por quem
            # observa, com a fonte declarada na nota de mapeamento.
            preco = args.preco
            if preco is None:
                print(
                    "markets-comparar: --preco é obrigatório. A busca ao vivo na Kalshi foi "
                    "removida (termos de terceiro). O comparador oficial passa a ser o consenso "
                    "Focus/BCB — dado público, e comparação DIRETA com o IPCA."
                )
                return 1
            sdk_comparar = None if args.no_audit else abrir_auditoria(Path("reports/audit/markets-ledger.db"))
            resultado = observar_divergencia(
                claim_id=args.claim,
                comparator_price=preco,
                ticker=args.ticker,
                nota_de_mapeamento=args.nota,
                comparator=args.comparador,
                sdk=sdk_comparar,
            )
        except (ComparadorError, ResolutionError, AuditoriaError) as error:
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
    if args.command == "markets-serie":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.markets.serie_p import SerieError, registrar_ponto, registrar_vivos

        try:
            sdk_serie = None if args.no_audit else abrir_auditoria(Path("reports/audit/markets-ledger.db"))
            if args.claim:
                resultado = registrar_ponto(claim_id=args.claim, observado_em=args.dia, sdk=sdk_serie)
                pontos = [resultado]
            else:
                varredura = registrar_vivos(observado_em=args.dia, sdk=sdk_serie)
                pontos = varredura["pontos"]
        except (SerieError, AuditoriaError) as error:
            print(f"markets-serie: {error}")
            return 1

        if args.json_out:
            print(
                json.dumps(
                    [p["registro"] | {"duplicate": p["duplicate"]} for p in pontos], ensure_ascii=False, indent=2
                )
            )
            return 0

        print("=" * 62)
        print("SÉRIE p(t) — o que se acreditava, e QUANDO")
        print("=" * 62)
        if not pontos:
            print("\nnenhum claim vivo — série não inventa ponto para mercado liquidado")
            return 0
        for item in pontos:
            reg, marca = item["registro"], "dedupe" if item["duplicate"] else "NOVO"
            print(
                f"\n{reg['claim_id']}  [{marca}]"
                f"\n  p = {reg['probability']:.4f}  |  observado em {reg['observado_em']}"
                f"\n  horizonte: {reg['horizonte_dias']} dia(s) até o deadline {reg['deadline']}"
            )
            if item["selagem"] is not None:
                selo = item["selagem"]
                estado_selo = "dedupe na cadeia" if selo.get("duplicate") else "EVENTO market.probability_point SELADO"
                print(f"  selagem: {estado_selo} — {selo['event_hash_sha256'][:16]}…")
        novos = sum(1 for p in pontos if not p["duplicate"])
        print(f"\n{novos} ponto(s) novo(s), {len(pontos) - novos} dedupe.")
        print("O horizonte aqui é contra o DEADLINE. A calibração RE-ANCORA contra")
        print("determination_date quando ele existir — o relógio da fonte, não o do fechamento.")
        return 0
    if args.command == "markets-consenso":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.markets.consenso import ConsensoError, medir, selar

        try:
            snap = medir()
            selagem = None
            if not args.no_audit:
                selagem = selar(abrir_auditoria(Path("reports/audit/markets-ledger.db")), snap)
        except (ConsensoError, AuditoriaError) as error:
            print(f"markets-consenso: {error}")
            return 1

        if args.json_out:
            print(json.dumps(snap, ensure_ascii=False, indent=2))
            return 0

        print("=" * 62)
        print("CONSENSO FOCUS — a linha de base, medida com honestidade")
        print("=" * 62)
        print(f"\npares (consenso vintage x realizado): {snap['n']}  |  mínimo para agregar: {snap['amostra_minima']}")
        for par in snap["pares"]:
            print(
                f"\n  {par['mes_referencia']}: Focus {par['consenso_focus']:.2f}% vs observado "
                f"{par['valor_observado']:.2f}%  ->  erro {par['erro_absoluto_focus']:.4f}pp [{par['regime']}]"
            )
        if snap["suficiente"]:
            print(f"\nMAE do Focus: {snap['mae_focus']:.4f}pp")
            for regime, dados in snap["por_regime"].items():
                mae = "—" if dados["mae"] is None else f"{dados['mae']:.4f}pp"
                print(f"  {regime:16} n={dados['n']:<3} MAE={mae}")
        else:
            print(f"\n{snap['metodo']}")
        print(f"\nRESSALVA OBRIGATÓRIA: {snap['dependencia_declarada']}")
        if selagem is not None:
            estado_selo = "dedupe" if selagem.get("duplicate") else "EVENTO market.consensus_benchmark SELADO"
            print(f"\nselagem: {estado_selo} — {selagem['event_hash_sha256'][:16]}…")
        return 0
    if args.command == "markets-calibracao":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.markets.calibracao import CalibracaoError
        from asus_theye.markets.calibracao import medir as medir_calibracao
        from asus_theye.markets.calibracao import selar as selar_calibracao

        try:
            snap = medir_calibracao()
            selagem = None
            if not args.no_audit:
                selagem = selar_calibracao(abrir_auditoria(Path("reports/audit/markets-ledger.db")), snap)
        except (CalibracaoError, AuditoriaError) as error:
            print(f"markets-calibracao: {error}")
            return 1

        if args.json_out:
            print(json.dumps(snap, ensure_ascii=False, indent=2))
            return 0

        print("=" * 62)
        print("CALIBRAÇÃO — a probabilidade declarada vale alguma coisa?")
        print("=" * 62)
        print(f"\npares utilizáveis: {snap['n']}  |  mínimo para agregar: {snap['amostra_minima']}")
        if snap["suficiente"]:
            print(f"\nBrier: {snap['brier']:.4f}")
            murphy = snap["murphy"] or {}
            print(
                f"  confiabilidade {murphy.get('confiabilidade')} (menor melhor) | "
                f"resolução {murphy.get('resolucao')} (maior melhor)"
            )
            for faixa in snap["por_horizonte"]:
                b = "—" if faixa["brier"] is None else f"{faixa['brier']:.4f}"
                print(f"  {faixa['faixa']:14} n={faixa['n']:<4} Brier={b}")
        else:
            print(f"\n{snap['metodo']}")
            print("\nexcluídos:")
            for motivo, qtd in snap["excluidos"].items():
                print(f"  {motivo.replace('_', ' '):26} {qtd}")
        if selagem is not None:
            estado_selo = "dedupe" if selagem.get("duplicate") else "EVENTO market.calibration SELADO"
            print(f"\nselagem: {estado_selo} — {selagem['event_hash_sha256'][:16]}…")
        return 0
    if args.command == "markets-global":
        from asus_theye.markets.fonte_worldbank import FonteWorldBankError, indicador_anual

        try:
            observacao = indicador_anual(args.indicador, args.pais, args.ano)
        except FonteWorldBankError as error:
            print(f"markets-global: {error}")
            return 1

        if observacao is None:
            # UNKNOWN honesto: 'não publicado' nunca vira zero
            saida = {"pais": args.pais.upper(), "ano": args.ano, "valor": None, "motivo": "ano não publicado"}
            print(
                json.dumps(saida, ensure_ascii=False)
                if args.json_out
                else f"{args.pais.upper()} {args.ano}: não publicado (UNKNOWN, nunca zero)"
            )
            return 0

        if args.json_out:
            print(json.dumps(observacao.as_dict(), ensure_ascii=False, indent=2))
            return 0

        print("=" * 62)
        print("FONTE GLOBAL — indicador macro sob licença permissiva")
        print("=" * 62)
        print(f"\n{observacao.nome_do_pais} ({observacao.pais_iso3}) — {observacao.ano}")
        print(f"  {observacao.nome_do_indicador}: {observacao.valor:.4f} [{observacao.unidade}]")
        print(f"  periodicidade: {observacao.periodicidade}")
        print(f"\natribuição (exigida pela licença): {observacao.atribuicao}")
        print(f"licença: {observacao.licenca} — permite uso comercial, cópia e redistribuição")
        return 0
    if args.command == "markets-reprecificar":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.markets.gerador import GeradorError
        from asus_theye.markets.reprecificar import ReprecificacaoError, reprecificar
        from asus_theye.markets.sinais_cambio import SinaisCambioError
        from asus_theye.markets.sinais_ipca import SinaisError
        from asus_theye.markets.sinais_juros import SinaisJurosError

        try:
            import json as _json

            registro_atual = _json.loads(args.store.read_text(encoding="utf-8"))
            alvo = next((m for m in registro_atual.get("mercados", []) if m.get("claim_id") == args.claim), None)
            if alvo is None:
                print(f"markets-reprecificar: {args.claim} não existe no registro")
                return 1
            area_alvo = str(alvo.get("market_area_id", "macro"))
            mes_alvo = str(alvo["mes_referencia"])
            limiar_alvo = float(alvo["limiar"])
            if area_alvo == "juros":
                from asus_theye.markets.sinais_juros import probabilidade_para_juros

                nova = probabilidade_para_juros(mes_alvo, limiar_alvo)
            elif area_alvo == "cambio":
                from asus_theye.markets.sinais_cambio import probabilidade_para_cambio

                nova = probabilidade_para_cambio(mes_alvo, limiar_alvo)
            else:
                from asus_theye.markets.sinais_ipca import probabilidade_para_ipca

                nova = probabilidade_para_ipca(mes_alvo, limiar_alvo)
            sdk_rep = None if args.no_audit else abrir_auditoria(Path("reports/audit/markets-ledger.db"))
            resultado = reprecificar(
                claim_id=args.claim, probabilidade=nova, motivo=args.motivo, store=args.store, sdk=sdk_rep
            )
        except (
            ReprecificacaoError,
            SinaisError,
            SinaisJurosError,
            SinaisCambioError,
            GeradorError,
            AuditoriaError,
        ) as error:
            print(f"markets-reprecificar: {error}")
            return 1

        if args.json_out:
            print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
            return 0
        if not resultado["reprecificado"]:
            print(f"markets-reprecificar: {resultado['motivo']}")
            return 0
        m = resultado["mudanca"]
        print("=" * 62)
        print("REPRECIFICAÇÃO — o valor antigo fica na corrente")
        print("=" * 62)
        print(
            f"\n{m['claim_id']}: {m['probabilidade_anterior']:.4f} -> {m['probabilidade_nova']:.4f} "
            f"({m['movimento']:+.4f})"
        )
        print(f"  motivo: {m['motivo']}")
        print(f"  sinal:  {m['gerador'].get('metodo', '—')}")
        if resultado["selagem"] is not None:
            selo = resultado["selagem"]
            estado_selo = "dedupe" if selo.get("duplicate") else "EVENTO market.repricing SELADO"
            print(f"  selagem: {estado_selo} — {selo['event_hash_sha256'][:16]}…")
        return 0
    if args.command == "projeto-fronteira":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.projeto.fronteira import FronteiraError, medir_fronteira, selar_fronteira
        from asus_theye.projeto.fronteira import relatorio as relatorio_da_fronteira

        try:
            snap = medir_fronteira()
            selagem = None
            if not args.no_audit:
                selagem = selar_fronteira(abrir_auditoria(Path("reports/audit/markets-ledger.db")), snap)
        except (FronteiraError, AuditoriaError) as error:
            print(f"projeto-fronteira: {error}")
            return 1

        if args.json_out:
            print(json.dumps(snap, ensure_ascii=False, indent=2))
        else:
            print(relatorio_da_fronteira(snap))
            if selagem is not None:
                estado_selo = "dedupe" if selagem.get("duplicate") else "EVENTO project.boundary SELADO"
                print(f"\nselagem: {estado_selo} — {selagem['event_hash_sha256'][:16]}…")
        # fronteira rompida SAI COM ERRO: o cron precisa gritar, não sussurrar
        return 0 if snap["intacta"] else 1
    if args.command == "markets-rodada":
        from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria
        from asus_theye.markets.reprecificar import ReprecificacaoError, rodada

        try:
            sdk_rodada = None if args.no_audit else abrir_auditoria(Path("reports/audit/markets-ledger.db"))
            resultado = rodada(sdk=sdk_rodada)
        except (ReprecificacaoError, AuditoriaError) as error:
            print(f"markets-rodada: {error}")
            return 1

        if args.json_out:
            print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
            return 0

        print("=" * 62)
        print("RODADA — o que a plataforma acredita hoje")
        print("=" * 62)
        print(f"\ndia {resultado['dia']}")
        for acao in resultado["acoes"]:
            if acao["acao"] == "reprecificado":
                print(f"  {acao['claim_id']:22} {acao['de']:.4f} -> {acao['para']:.4f}")
            else:
                print(f"  {acao['claim_id']:22} {acao['acao']}  {acao.get('motivo', '')[:50]}")
        print(f"\n{resultado['reprecificados']} reprecificado(s), {resultado['estaveis']} estável(is).")
        print("Ponto de série gravado em TODOS — dia sem movimento também é informação.")
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
            "frescor": "frescor das fontes",
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

        resultado = exportar(args.out, publico=args.publico)
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
