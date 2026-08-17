"""Testes da ponte com o banco medido.

Duas camadas:

- **Determinística** — constrói um DuckDB sintético minúsculo (mesmo esquema) num
  diretório temporário. Roda sempre que ``duckdb`` estiver instalado; prova a
  mecânica (recuperação de ``p``, tradução para o domínio, tie-out contrato a
  contrato, e os guards da doutrina).
- **Integração** — só roda se ``ASUS_MARKETS_DB`` apontar para o banco real.
  Prova o tie-out contra os números publicados no classificador (voto 0,003293,
  macro 0,111089) e o total de 41 liquidados.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from asus_theye.markets import (
    MarketsSourceError,
    load_settled,
    reconcile,
    recover_probability,
    resolve_db_path,
    skill_report,
)

duckdb = pytest.importorskip("duckdb")


# --------------------------------------------------------------- fixture sintética


def _build_db(path: Path, rows: list[dict]) -> None:
    """Cria um asus_teste.duckdb minúsculo com mercados + resolucoes."""
    con = duckdb.connect(str(path))
    con.execute(
        "create table mercados (id varchar, produto varchar, etiqueta varchar, "
        "pergunta_leiga varchar, data_abertura varchar, data_limite varchar, "
        "fonte_resolucao varchar, criterio_resolucao varchar, limiar double, status varchar)"
    )
    con.execute(
        "create table resolucoes (mercado_id varchar, timestamp varchar, resultado_real integer, "
        "valor_observado double, brier_do_contrato double, acerto integer, fonte_confirmacao varchar)"
    )
    for r in rows:
        p, o = r["probability"], r["outcome"]
        brier = round((p - o) ** 2, 8)
        con.execute(
            "insert into mercados values (?,?,?,?,?,?,?,?,?,?)",
            [
                r["id"],
                r["produto"],
                "ETI",
                r.get("q", "?"),
                "2026-07-01T00:00:00Z",
                "2026-07-14",
                r.get("fonte", "Fonte Oficial X"),
                "criterio",
                0.5,
                "LIQUIDADO",
            ],
        )
        con.execute(
            "insert into resolucoes values (?,?,?,?,?,?,?)",
            [r["id"], "2026-07-20T00:00:00Z", o, 0.0, brier, 1, r.get("fonte", "Fonte Oficial X")],
        )
    con.close()


@pytest.fixture
def synthetic_db(tmp_path: Path) -> str:
    db = tmp_path / "mini.duckdb"
    _build_db(
        db,
        [
            {"id": "JUROS-01", "produto": "juros", "probability": 0.30, "outcome": 1},
            {"id": "CAMBIO-01", "produto": "cambio", "probability": 0.80, "outcome": 0},
        ],
    )
    return str(db)


# --------------------------------------------------------------- mecânica


@pytest.mark.parametrize("outcome,prob", [(1, 0.912), (0, 0.3333), (1, 1.0), (0, 0.0), (1, 0.5)])
def test_recover_probability_reproduz_p(outcome: int, prob: float) -> None:
    brier = (prob - outcome) ** 2
    assert recover_probability(outcome, brier) == pytest.approx(prob, abs=1e-9)


def test_recover_probability_rejeita_desfecho_e_brier_invalidos() -> None:
    with pytest.raises(MarketsSourceError):
        recover_probability(2, 0.1)
    with pytest.raises(MarketsSourceError):
        recover_probability(1, -0.1)


def test_load_settled_traduz_para_o_dominio(synthetic_db: str) -> None:
    contracts = load_settled(synthetic_db)
    assert len(contracts) == 2
    by_id = {c.claim.claim_id: c for c in contracts}
    juros = by_id["JUROS-01"]
    assert juros.claim.market_area_id == "juros"  # produto -> área
    assert juros.resolution.outcome == 1
    assert juros.probability == pytest.approx(0.30, abs=1e-6)
    # tie-out contrato a contrato: brier recuperado == brier do banco
    from asus_theye.markets import brier_score

    assert brier_score([(juros.probability, 1)]) == pytest.approx(juros.db_brier, abs=1e-6)


def test_reconcile_tie_out_por_contrato(synthetic_db: str) -> None:
    rep = reconcile(synthetic_db)
    assert rep["settled_total"] == 2
    assert all(area["per_contract_matches"] for area in rep["areas"]), "cada contrato reproduz o brier do banco"


def test_skill_report_declara_janela_por_area(synthetic_db: str) -> None:
    rep = skill_report(synthetic_db)
    assert rep["settled_total"] == 2
    areas = {a["area_id"]: a for a in rep["areas"]}
    # janela sempre presente, uma por área
    assert all(a["window"].endswith(f"({a['area_id']})") for a in rep["areas"])
    # juros: 1 contrato, desfecho 1 -> taxa-base 1.0 -> baseline perfeito -> skill indefinida
    assert areas["juros"]["skill_score"] is None
    assert areas["juros"]["baseline_beats_model"] is True


def test_skill_report_baseline_externo_muda_a_resposta(synthetic_db: str) -> None:
    # com um baseline externo != desfecho, a skill deixa de ser indefinida
    rep = skill_report(synthetic_db, baseline_probability=0.7)
    juros = next(a for a in rep["areas"] if a["area_id"] == "juros")
    assert juros["skill_score"] is not None
    assert juros["baseline_probability"] == pytest.approx(0.7)


def test_kalshi_como_fonte_no_banco_levanta(tmp_path: Path) -> None:
    db = tmp_path / "hostil.duckdb"
    _build_db(db, [{"id": "X-01", "produto": "juros", "probability": 0.5, "outcome": 1, "fonte": "Kalshi"}])
    with pytest.raises(MarketsSourceError, match="Kalshi|proibida"):
        load_settled(str(db))


def test_produto_desconhecido_levanta(tmp_path: Path) -> None:
    db = tmp_path / "estranho.duckdb"
    _build_db(db, [{"id": "Y-01", "produto": "nao_existe", "probability": 0.5, "outcome": 1}])
    with pytest.raises(MarketsSourceError, match="sem área|produto"):
        load_settled(str(db))


def test_caminho_ausente_levanta() -> None:
    with pytest.raises(MarketsSourceError, match="não informado|não encontrado"):
        resolve_db_path("/caminho/que/nao/existe/x.duckdb")


# --------------------------------------------------------------- integração (banco real)

_REAL_DB = os.environ.get("ASUS_MARKETS_DB", "")


@pytest.mark.skipif(not _REAL_DB or not Path(_REAL_DB).exists(), reason="ASUS_MARKETS_DB não aponta para um banco real")
def test_tie_out_contra_o_banco_real() -> None:
    rep = reconcile(_REAL_DB)
    assert rep["settled_total"] == 41, "40 voto + 1 macro liquidados"
    areas = {a["area_id"]: a for a in rep["areas"]}

    voto = areas["voto-legislativo"]
    assert voto["n"] == 40
    assert voto["module_brier"] == pytest.approx(0.003293, abs=1e-6)
    assert voto["aggregate_matches"] and voto["per_contract_matches"]

    macro = areas["macroeconomia"]
    assert macro["module_brier"] == pytest.approx(0.111089, abs=1e-6)
    assert macro["aggregate_matches"]

    assert rep["tie_out"], "módulo reproduz o banco e o classificador, contrato a contrato"
