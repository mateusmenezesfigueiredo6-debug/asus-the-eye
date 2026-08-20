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

# estado deixou de ser decorativo: cada valor conhecido tem uma faixa de
# peso_concluido coerente com ele. "parcial" cobre o meio do caminho; um
# estado fora deste dicionário passa sem checagem de coerência (extensível).
_ESTADOS_COERENTES = {
    "concluida": lambda peso: peso == 1.0,
    "pendente": lambda peso: peso == 0.0,
    "parcial": lambda peso: 0.0 < peso < 1.0,
}

# A medição EXCLUI retrospectivos (o próprio dado se declara não-previsão) e
# medições do projeto (senão a medição contaria a si mesma). O que sobra é o
# que a corrente PROVA em termos prospectivos de mercado.
_EVENTOS_SEM_CAPACIDADE_REAL = {"market.retrospective_import", "project.measurement"}


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

        peso_relativo = fase.get("peso_relativo", 1.0)
        if (
            not isinstance(peso_relativo, (int, float))
            or isinstance(peso_relativo, bool)
            or float(peso_relativo) <= 0.0
        ):
            raise MedicaoError(f"{fase.get('id')}: peso_relativo deve ser > 0, veio {peso_relativo!r}")

        estado = fase.get("estado")
        coerente = _ESTADOS_COERENTES.get(estado) if isinstance(estado, str) else None
        if coerente is not None and not coerente(float(peso)):
            raise MedicaoError(
                f"{fase.get('id')}: estado {estado!r} incoerente com peso_concluido={peso!r} "
                "— estado deixou de ser decorativo, ou os dois batem ou a fase é rejeitada"
            )

        criterio = fase.get("criterio_verificavel")
        if criterio is not None and not str(criterio).strip():
            raise MedicaoError(f"{fase.get('id')}: criterio_verificavel declarado mas vazio")
    return fases


def _pct(fases: list[dict[str, Any]]) -> float:
    peso_total = sum(float(f.get("peso_relativo", 1.0)) for f in fases)
    concluido = sum(float(f["peso_concluido"]) * float(f.get("peso_relativo", 1.0)) for f in fases)
    return round(100.0 * concluido / peso_total, 1)


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
        "metodo": (
            "média ponderada (peso_relativo) dos pesos declarados por fase em "
            "reports/projeto/produtos.json (roteiro até os 2 produtos)"
        ),
        "fases": fases,
    }


def _capacidade_real(
    todos_eventos: list[dict[str, Any]],
    mercados: list[dict[str, Any]],
    resolucoes: list[dict[str, Any]],
) -> dict[str, Any]:
    """O que a corrente PROVA, separado do que as fases DECLARAM.

    O placar de fases pode dizer "90%" sem nenhum mercado real ter nascido do
    modelo. Este eixo conta a atividade prospectiva de verdade: eventos que não
    são import retrospectivo nem medição de projeto, claims cujo preço nasceu
    de um gerador (bloco 'gerador' no registro, não p=0,50 default), liquidações
    reais e observações de divergência contra comparadores externos.
    """
    prospectivos = [e for e in todos_eventos if e.get("event_type") not in _EVENTOS_SEM_CAPACIDADE_REAL]
    return {
        "eventos_prospectivos": len(prospectivos),
        "claims_com_gerador": sum(1 for m in mercados if "gerador" in m),
        "liquidacoes": len(resolucoes),
        "observacoes_comparador": sum(1 for e in todos_eventos if e.get("event_type") == "market.comparator"),
        "metodo": (
            "reports/markets/{eventos.jsonl,registro.json,resolucoes.jsonl} — conta o que a "
            "corrente PROVA, não o que as fases declaram: eventos_prospectivos exclui "
            "market.retrospective_import e project.measurement; claims_com_gerador exige o "
            "bloco 'gerador' (nasceu do modelo, não é p=0,50 default); liquidacoes vem de "
            "resolucoes.jsonl; observacoes_comparador conta market.comparator. É o número que "
            "o placar de fases sozinho não consegue mostrar."
        ),
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
            "metodo": "média ponderada (peso_relativo) dos pesos declarados por fase em reports/projeto/fases.json",
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
        "capacidade_real": _capacidade_real(todos_eventos, mercados, resolucoes),
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
