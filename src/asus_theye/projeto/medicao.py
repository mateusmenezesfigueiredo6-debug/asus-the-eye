# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Medição do projeto — quanto falta, com método declarado e SEMPRE em hash.

O placar do projeto vira um snapshot determinístico: cada número carrega o
método de onde saiu, o snapshot inteiro ganha um hash canônico, e a selagem na
cadeia auditável registra cada MUDANÇA de estado (mesmo estado = dedupe, estado
novo = evento novo). "Existe como artefato" ≠ "roda de verdade" — os eixos são
separados de propósito.

Determinismo: o snapshot NÃO contém relógio. A identidade da medição é o
estado do projeto, não a hora em que alguém olhou. Por isso o hash é estável
entre duas medições do mesmo estado, e a selagem é naturalmente idempotente.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import hash_json, verify_chain

BASE_PADRAO = Path("reports")
FASES_PADRAO = Path("reports/projeto/fases.json")


class MedicaoError(RuntimeError):
    """Insumo da medição corrompido. Sempre levanta — nunca inventa número."""


def _jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def _fases(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        raise MedicaoError(f"fases não declaradas: {caminho} — a medição exige o método, não chuta")
    fases = json.loads(caminho.read_text(encoding="utf-8"))["fases"]
    _validar_fases(fases)
    return fases


def _validar_fases(fases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for fase in fases:
        peso = fase.get("peso_concluido")
        if not isinstance(peso, (int, float)) or isinstance(peso, bool) or not 0.0 <= float(peso) <= 1.0:
            raise MedicaoError(f"{fase.get('id')}: peso_concluido deve estar em [0,1], veio {peso!r}")
        if not fase.get("metodo"):
            raise MedicaoError(f"{fase.get('id')}: fase sem 'metodo' — número sem método não entra")
    return fases


def _pct(fases: list[dict[str, Any]]) -> float:
    return round(100.0 * sum(float(f["peso_concluido"]) for f in fases) / len(fases), 1)


def _roteiro_de_produtos(caminho: Path) -> dict[str, Any]:
    """Segundo checklist (roteiro até os produtos) — opcional, mas com método sempre.

    O caminho mínimo F0–F5 é obrigatório e histórico; o roteiro dos produtos é
    declarado quando existe. Ausente não é 0% — é "não declarado", dito como tal.
    """
    if not caminho.exists():
        return {"pct": None, "fases": [], "metodo": f"{caminho} ausente — roteiro não declarado"}
    fases = _validar_fases(json.loads(caminho.read_text(encoding="utf-8"))["fases"])
    return {
        "pct": _pct(fases),
        "metodo": "média dos pesos declarados por fase em reports/projeto/produtos.json (roteiro até os 2 produtos)",
        "fases": fases,
    }


def medir_projeto(base: Path = BASE_PADRAO, *, fases_path: Path | None = None) -> dict[str, Any]:
    """Snapshot determinístico do projeto, com método por eixo e hash canônico."""
    markets = base / "markets"
    fases = _fases(fases_path or (base / "projeto" / "fases.json"))
    todos_eventos = _jsonl(markets / "eventos.jsonl")
    # A medição EXCLUI os próprios eventos de medição (project.measurement):
    # senão cada selagem mudaria o estado que ela mede e o hash nunca
    # estabilizaria — um laço infinito de eventos. Medição mede o negócio.
    eventos = [e for e in todos_eventos if e.get("event_type") != "project.measurement"]
    resolucoes = _jsonl(markets / "resolucoes.jsonl")
    ancoras = _jsonl(markets / "ancoras.jsonl")

    mercados: list[dict[str, Any]] = []
    registro_path = markets / "registro.json"
    if registro_path.exists():
        mercados = json.loads(registro_path.read_text(encoding="utf-8")).get("mercados", [])

    chart_tests: int | None = None
    chart_path = base / "chart" / "snapshot.json"
    if chart_path.exists():
        chart_tests = json.loads(chart_path.read_text(encoding="utf-8")).get("totals", {}).get("tests")

    snapshot: dict[str, Any] = {
        "versao": 2,
        "caminho_minimo": {
            "pct": _pct(fases),
            "metodo": "média dos pesos declarados por fase em reports/projeto/fases.json",
            "fases": fases,
        },
        "produtos": _roteiro_de_produtos(base / "projeto" / "produtos.json"),
        "corrente": {
            "eventos": len(eventos),
            "topo_hash": eventos[-1]["event_hash_sha256"] if eventos else None,
            "verifica": verify_chain(todos_eventos),
            "metodo": (
                "reports/markets/eventos.jsonl — verify_chain sobre a corrente inteira; "
                "contagem e topo EXCLUEM project.measurement (a medição mede o negócio, "
                "não a si mesma — senão o hash nunca estabilizaria)"
            ),
        },
        "medicao_continua": {
            "mercados": len(mercados),
            "liquidados": sum(1 for m in mercados if m.get("estado") == "LIQUIDADO"),
            "resolucoes": len(resolucoes),
            "metodo": "reports/markets/{registro.json,resolucoes.jsonl}",
        },
        "ancoragem": {
            "ancoras": len(ancoras),
            "metodo": "reports/markets/ancoras.jsonl (0 = broadcast aguardando o dono)",
        },
        "mlops": {
            "modelos": len(_jsonl(base / "mlops" / "modelos.jsonl")),
            "corridas": len(_jsonl(base / "mlops" / "corridas.jsonl")),
            "metodo": (
                "reports/mlops/{modelos,corridas}.jsonl — contagem do store; "
                "corridas selam como ml.run quando a auditoria está aberta"
            ),
        },
        "chart": {
            "tests": chart_tests,
            "metodo": "reports/chart/snapshot.json — mede EXISTÊNCIA de artefato, não execução",
        },
        "ressalva": "Nenhum número sem método. 'Existe como artefato' ≠ 'roda de verdade'.",
    }
    snapshot["hash_da_medicao"] = hash_json(snapshot)
    return snapshot


def selar_projeto(
    sdk: Any,
    snapshot: dict[str, Any] | None = None,
    *,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Sela a medição do projeto na cadeia. Mesmo estado = dedupe; novo = evento.

    A correlação deriva do hash da medição: o estado é a identidade. O recibo
    volta com ``duplicate=True`` quando o projeto não mudou desde a última selagem.
    """
    from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

    snap = snapshot or medir_projeto()
    return selar_registro(
        sdk,
        snap,
        tipo_evento="project.measurement",
        recurso="project",
        correlation_id=f"projeto:{snap['hash_da_medicao'][:32]}",
        eventos=eventos or EVENTOS_PADRAO,
    )
