"""Produtores de corridas — quem já mede vira fonte do rastreio ML.

Primeiro produtor: a suíte de benchmark (``benchmark/runner.py``), que já
emite relatório com hash e ledger próprio. Aqui o relatório é traduzido para
uma :class:`~asus_theye.mlops.rastreio.Corrida` — params explícitos, métricas
numéricas e o artefato (``latest.json``) com SHA-256 — pronto para selar.
"""

from __future__ import annotations

import hashlib
from importlib import metadata
from pathlib import Path
from typing import Any

from asus_theye.mlops.rastreio import Corrida, Modelo, Versao

MODELO_BENCHMARK = Modelo(
    modelo_id="qaoa-benchmark",
    nome="Suíte de benchmark QAOA × clássico",
    area="quantum",
    objetivo="medir o QAR (razão de vantagem quântica) do QAOA local contra o solver clássico no problema demo",
)


def _versao_pacote() -> str:
    try:
        return metadata.version("asus-the-eye")
    except metadata.PackageNotFoundError:  # pragma: no cover - editable quebrado
        return "0.0.0"


def versao_do_benchmark() -> Versao:
    """A versão rastreada é a do pacote: o código da suíte muda com o release."""
    return Versao(
        modelo_id=MODELO_BENCHMARK.modelo_id,
        versao=_versao_pacote(),
        origem="asus_theye.benchmark.runner.run_benchmark_suite",
    )


def corrida_do_benchmark(
    report: dict[str, Any],
    report_path: Path,
    *,
    shots: int,
    layers: int,
    seed: int,
    stability_runs: int,
) -> Corrida:
    """Traduz o relatório da suíte para uma corrida rastreável (sem rodar nada)."""
    return Corrida(
        modelo_id=MODELO_BENCHMARK.modelo_id,
        versao=_versao_pacote(),
        params={
            "problema": report["problem"]["name"],
            "shots": shots,
            "layers": layers,
            "seed": seed,
            "stability_runs": stability_runs,
        },
        metricas={
            "qar": float(report["metrics"]["qar"]["qar"]),
            "score_classico": float(report["results"]["classical"]["score"]),
            "score_qaoa": float(report["results"]["qaoa"]["score"]),
            "estabilidade_desvio": float(report["metrics"]["stability"]["standard_deviation"]),
        },
        artefatos=[{"caminho": str(report_path), "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest()}],
        executada_em=str(report["date"]),
    )
