"""Ponte entre o banco medido (``asus_teste.duckdb``) e o domínio ``markets``.

O trabalho medido — 50 mercados, 41 liquidados — vive **fora** do repositório,
no DuckDB do projeto asus. Este módulo LÊ esse banco (nunca escreve, nunca copia
os dados para o repo: a licença de ``data/`` é restrita) e o traduz para os
objetos do domínio, de modo que a mesma doutrina que governa ``markets/`` passe
a governar os dados reais.

A probabilidade que o modelo atribuiu não está gravada, mas é **recuperável** dos
contratos liquidados: como ``brier = (p - desfecho)²``, então
``p = desfecho ± √brier``, e a raiz em ``[0, 1]`` é única. Reconciliar é
reproduzir, pelo ``scoring`` do módulo, o ``brier_do_contrato`` que o banco já
gravou — se baterem contrato a contrato e no agregado publicado, a ponte é fiel.

O banco não entra pelo import: ``duckdb`` é o extra opcional ``[markets]``, e o
caminho vem de ``ASUS_MARKETS_DB`` ou do argumento ``path``.
"""

from __future__ import annotations

import math
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from asus_theye.markets.claim import (
    UNCERTAINTY_TOLERANCE,
    MarketClaim,
    _is_forbidden,
    load_classifier,
)
from asus_theye.markets.resolution import Resolution
from asus_theye.markets.scoring import brier_score, skill_score

DB_ENV = "ASUS_MARKETS_DB"  # aponta para o asus_teste.duckdb (fora do repo)
TIE_OUT_TOLERANCE = 1e-6


class MarketsSourceError(RuntimeError):
    """Banco ausente, esquema incompatível ou linha que viola a doutrina. Sempre levanta."""


def resolve_db_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Resolve o caminho do banco: argumento explícito ou ``ASUS_MARKETS_DB``."""
    raw = path or os.environ.get(DB_ENV)
    if not raw:
        raise MarketsSourceError(
            f"caminho do banco não informado: passe path= ou defina {DB_ENV}. "
            "O asus_teste.duckdb vive fora do repositório (licença restrita de data/)."
        )
    resolved = Path(raw).expanduser()
    if not resolved.exists():
        raise MarketsSourceError(f"banco não encontrado: {resolved}")
    return resolved


def _connect(path: Path) -> Any:
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise MarketsSourceError("duckdb não instalado. Instale o extra: pip install 'asus-the-eye[markets]'") from exc
    return duckdb.connect(str(path), read_only=True)


def produto_to_area(classifier: dict[str, Any] | None = None) -> dict[str, str]:
    """Mapa ``produto`` (no banco) → ``market_area_id`` (no classificador)."""
    classifier = classifier or load_classifier()
    return {area["produto"]: area["market_area_id"] for area in classifier["areas"]}


def recover_probability(outcome: int, brier: float) -> float:
    """Recupera ``p`` de ``brier = (p - desfecho)²``. Raiz única em ``[0, 1]``."""
    if outcome not in (0, 1):
        raise MarketsSourceError(f"desfecho deve ser 0 ou 1, veio {outcome!r}")
    if brier < 0.0:
        raise MarketsSourceError(f"brier negativo no banco: {brier!r}")
    distance = math.sqrt(brier)
    probability = (outcome - distance) if outcome == 1 else (outcome + distance)
    return min(1.0, max(0.0, probability))


@dataclass(frozen=True)
class SettledContract:
    """Um contrato liquidado do banco, traduzido para os objetos do domínio."""

    claim: MarketClaim
    resolution: Resolution
    db_brier: float  # brier_do_contrato gravado no banco (a verdade a reproduzir)
    probability: float  # recuperada de brier + desfecho

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim.as_dict(),
            "resolution": self.resolution.as_dict(),
            "db_brier": self.db_brier,
            "probability": self.probability,
        }


_SETTLED_QUERY = """
    select
        m.id             as id,
        m.produto        as produto,
        m.pergunta_leiga as pergunta_leiga,
        m.data_abertura  as data_abertura,
        m.data_limite    as data_limite,
        m.fonte_resolucao as fonte_resolucao,
        r.resultado_real as resultado_real,
        r.brier_do_contrato as brier_do_contrato,
        r.fonte_confirmacao as fonte_confirmacao,
        r.timestamp      as resolved_at
    from resolucoes r
    join mercados m on m.id = r.mercado_id
"""


def load_settled(path: str | os.PathLike[str] | None = None) -> list[SettledContract]:
    """Carrega os contratos liquidados do banco como objetos do domínio.

    Constrói ``MarketClaim``/``Resolution`` diretamente (não via ``make_claim``)
    para preservar a fonte e o prazo exatos do banco, mas ainda faz valer os dois
    invariantes duros: o produto tem de existir no classificador, e a fonte nunca
    pode ser Kalshi.
    """
    prod2area = produto_to_area()
    connection = _connect(resolve_db_path(path))
    try:
        cursor = connection.execute(_SETTLED_QUERY)
        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    finally:
        connection.close()

    contracts: list[SettledContract] = []
    for row in rows:
        produto = row["produto"]
        if produto not in prod2area:
            raise MarketsSourceError(
                f"{row['id']}: produto {produto!r} sem área no classificador (data/domains/mercados_preditivos.json)"
            )
        source = row["fonte_resolucao"]
        if _is_forbidden(source):
            raise MarketsSourceError(f"{row['id']}: fonte {source!r} proibida — Kalshi nunca resolve")

        outcome = int(row["resultado_real"])
        brier = float(row["brier_do_contrato"])
        probability = recover_probability(outcome, brier)
        area_id = prod2area[produto]

        claim = MarketClaim(
            claim_id=str(row["id"]),
            market_area_id=area_id,
            question=str(row["pergunta_leiga"]),
            deadline=str(row["data_limite"]),
            probability=probability,
            resolution_source=str(source),
            created_at=str(row["data_abertura"]),
            max_uncertainty=abs(probability - 0.5) <= UNCERTAINTY_TOLERANCE,
        )
        resolution = Resolution(
            claim_id=str(row["id"]),
            market_area_id=area_id,
            outcome=outcome,
            resolution_source=str(row["fonte_confirmacao"]),
            resolved_at=str(row["resolved_at"]),
        )
        contracts.append(SettledContract(claim=claim, resolution=resolution, db_brier=brier, probability=probability))

    return contracts


def reconcile(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Reconcilia o ``scoring`` do módulo contra o banco e o classificador.

    Para cada área liquidada devolve: o Brier que o módulo calcula, o Brier
    publicado no classificador, se batem, e se cada contrato reproduz o
    ``brier_do_contrato`` do banco. ``tie_out`` só é ``True`` se tudo bate.
    """
    settled = load_settled(path)
    published = {area["market_area_id"]: area for area in load_classifier()["areas"]}

    by_area: dict[str, list[SettledContract]] = defaultdict(list)
    for contract in settled:
        by_area[contract.claim.market_area_id].append(contract)

    areas_report: list[dict[str, Any]] = []
    tie_out = True
    for area_id, contracts in sorted(by_area.items()):
        pairs = [(c.probability, c.resolution.outcome) for c in contracts]
        module_brier = brier_score(pairs)
        published_brier = published.get(area_id, {}).get("brier")
        aggregate_matches = (
            module_brier is not None
            and published_brier is not None
            and abs(module_brier - float(published_brier)) < TIE_OUT_TOLERANCE
        )
        per_contract_ok = all(
            abs((brier_score([(c.probability, c.resolution.outcome)]) or 0.0) - c.db_brier) < TIE_OUT_TOLERANCE
            for c in contracts
        )
        tie_out = tie_out and aggregate_matches and per_contract_ok
        areas_report.append(
            {
                "area_id": area_id,
                "n": len(contracts),
                "module_brier": module_brier,
                "published_brier": published_brier,
                "aggregate_matches": aggregate_matches,
                "per_contract_matches": per_contract_ok,
            }
        )

    return {
        "settled_total": len(settled),
        "areas": areas_report,
        "tie_out": tie_out,
    }


def skill_report(
    path: str | os.PathLike[str] | None = None,
    *,
    baseline_probability: float | None = None,
) -> dict[str, Any]:
    """Skill por área contra um palpite constante, com a janela declarada.

    ``baseline_probability=None`` usa a taxa-base observada de cada área (um
    palpite constante honesto in-sample). Passar um valor fixa o mesmo baseline
    para todas as áreas — útil, por exemplo, para medir o voto contra a taxa
    histórica de seguimento partidário (0,959126), onde o baseline vence o modelo.

    Áreas cujo desfecho é constante (ex.: voto, todos 1) têm taxa-base perfeita e,
    sem baseline externo, a skill fica indefinida — é o limiar de máxima incerteza,
    não uma falha.
    """
    settled = load_settled(path)
    by_area: dict[str, list[SettledContract]] = defaultdict(list)
    for contract in settled:
        by_area[contract.claim.market_area_id].append(contract)

    areas_report: list[dict[str, Any]] = []
    for area_id, contracts in sorted(by_area.items()):
        pairs = [(c.probability, c.resolution.outcome) for c in contracts]
        result = skill_score(
            pairs,
            window=f"{len(contracts)} contratos ({area_id})",
            baseline_probability=baseline_probability,
        )
        areas_report.append({"area_id": area_id, **result})

    return {"settled_total": len(settled), "areas": areas_report}
