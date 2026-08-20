# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da plataforma comercial.

O que estes testes protegem não é o funil — é a honestidade dos números que ele
produz. Taxa sem denominador, amostra pequena ranqueada, perda sem motivo e nome
de cliente vazando são os quatro jeitos de esse sistema mentir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.commercial import (
    MINIMUM_SAMPLE,
    OpportunityError,
    Pipeline,
    compute_metrics,
    load_niches,
    new_opportunity,
    niche_for_legal_areas,
    rank_niches,
)
from asus_theye.commercial.niches import NicheError, classify_case, niche_by_id
from asus_theye.commercial.pipeline import ALLOWED_TRANSITIONS, STAGES, pseudonymize

PERIOD = {"period_start": "2026-01-01", "period_end": "2026-12-31"}
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "commercial"


def pipeline(tmp_path: Path) -> Pipeline:
    return Pipeline(tmp_path / "pipeline.jsonl")


def seed(pipe: Pipeline, niche_id: str, *, won: int = 0, lost: int = 0, open_: int = 0) -> None:
    for index in range(won):
        opportunity = pipe.add(
            new_opportunity(niche_id=niche_id, client_identifier=f"g{index}", source_channel="indicacao")
        )
        pipe.advance(opportunity["opportunity_id"], "qualificacao")
        pipe.advance(opportunity["opportunity_id"], "proposta")
        pipe.advance(opportunity["opportunity_id"], "ganho", value_brl=10_000.0)
    for index in range(lost):
        opportunity = pipe.add(new_opportunity(niche_id=niche_id, client_identifier=f"p{index}", source_channel="site"))
        pipe.advance(opportunity["opportunity_id"], "perdido", lost_reason="preco")
    for index in range(open_):
        pipe.add(new_opportunity(niche_id=niche_id, client_identifier=f"a{index}", source_channel="evento"))


# ------------------------------------------------------------------- nichos


def test_fifteen_niches_all_referencing_real_legal_areas() -> None:
    niches = load_niches()
    assert len(niches) == 15
    assert len({n["niche_id"] for n in niches}) == 15  # load_niches já valida as áreas


def test_niche_is_configuration_not_code() -> None:
    """Acrescentar o 16º nicho é uma entrada de JSON — não existe módulo por nicho."""
    registry = json.loads((DATA_DIR / "niches.json").read_text(encoding="utf-8"))
    assert registry["niche_count"] == len(registry["niches"])
    modules = list((Path(__file__).resolve().parents[2] / "src" / "asus_theye" / "commercial").glob("*.py"))
    assert len(modules) <= 5, "um módulo por nicho seria o erro que esta arquitetura evita"


def test_legal_taxonomy_bridges_into_commercial_niche() -> None:
    """O classificador dos 145 nichos jurídicos alimenta o comercial sem duplicação."""
    assert niche_for_legal_areas(["agribusiness"]) == "agronegocio"
    assert niche_for_legal_areas(["tax", "customs"]) == "tributario"
    assert niche_for_legal_areas(["area-inexistente"]) is None


def test_classify_case_end_to_end() -> None:
    result = classify_case("Ação de cobrança fundada em CPR do agronegócio")
    assert result["niche_id"] == "agronegocio"
    assert "agribusiness" in result["legal_area_ids_suggested"]


def test_unclassifiable_text_stays_silent() -> None:
    result = classify_case("texto generico sem materia juridica alguma")
    assert result["niche_id"] is None
    assert result["claim_class"] == "UNKNOWN"


def test_unknown_niche_raises() -> None:
    with pytest.raises(NicheError, match="desconhecido"):
        niche_by_id("nao-existe")


# ------------------------------------------------------------- privacidade


def test_client_name_is_never_stored(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    pipe.add(
        new_opportunity(
            niche_id="tributario",
            client_identifier="Construtora Silva e Filhos LTDA",
            source_channel="indicacao",
            notes="cliente indicado pelo Dr. Fulano, fatura R$ 40 milhões",
        )
    )
    raw = pipe.path.read_text(encoding="utf-8")
    assert "Silva" not in raw
    assert "Fulano" not in raw
    assert "40 milhões" not in raw
    assert "cli-" in raw


def test_pseudonym_is_stable_and_irreversible() -> None:
    first = pseudonymize("Construtora Silva")
    assert first == pseudonymize("  construtora silva  "), "mesmo cliente, mesma referência"
    assert first != pseudonymize("Construtora Souza")
    assert "silva" not in first.lower()


# ------------------------------------------------------------------- funil


def test_pipeline_is_append_only(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    opportunity = pipe.add(new_opportunity(niche_id="contratos", client_identifier="c1", source_channel="site"))
    pipe.advance(opportunity["opportunity_id"], "qualificacao")
    pipe.advance(opportunity["opportunity_id"], "proposta")
    history = pipe.history(opportunity["opportunity_id"])
    assert [r["stage"] for r in history] == ["entrada", "qualificacao", "proposta"]
    assert len(pipe.opportunities()) == 1, "o funil mostra o estado atual, o histórico permanece"


def test_invalid_transition_is_refused(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    opportunity = pipe.add(new_opportunity(niche_id="contratos", client_identifier="c1", source_channel="site"))
    with pytest.raises(OpportunityError, match="transição inválida"):
        pipe.advance(opportunity["opportunity_id"], "ganho")  # sem proposta não há o que ganhar


def test_losing_requires_a_reason(tmp_path: Path) -> None:
    """Perder sem motivo registrado não ensina nada."""
    pipe = pipeline(tmp_path)
    opportunity = pipe.add(new_opportunity(niche_id="contratos", client_identifier="c1", source_channel="site"))
    with pytest.raises(OpportunityError, match="motivo"):
        pipe.advance(opportunity["opportunity_id"], "perdido")


def test_winning_requires_a_registered_value(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    opportunity = pipe.add(new_opportunity(niche_id="contratos", client_identifier="c1", source_channel="site"))
    pipe.advance(opportunity["opportunity_id"], "qualificacao")
    pipe.advance(opportunity["opportunity_id"], "proposta")
    with pytest.raises(OpportunityError, match="valor registrado"):
        pipe.advance(opportunity["opportunity_id"], "ganho")


def test_closed_stages_are_terminal() -> None:
    assert ALLOWED_TRANSITIONS["ganho"] == ()
    assert ALLOWED_TRANSITIONS["perdido"] == ()
    assert set(ALLOWED_TRANSITIONS) == set(STAGES)


def test_history_reconstructs_the_past(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    opportunity = pipe.add(new_opportunity(niche_id="contratos", client_identifier="c1", source_channel="site"))
    created = opportunity["created_at"]
    pipe.advance(opportunity["opportunity_id"], "qualificacao")
    past = pipe.opportunities(as_of=created)
    assert past[0]["stage"] == "entrada", "o funil de ontem é reconstruível"


# --------------------------------------------------------------- métricas


def test_no_closings_produces_null_rate_not_zero(tmp_path: Path) -> None:
    """Taxa sem denominador não é 0% — é indisponível."""
    pipe = pipeline(tmp_path)
    seed(pipe, "tributario", open_=5)
    metrics = compute_metrics(pipe.opportunities(), "tributario", **PERIOD)
    assert metrics["win_rate"] is None
    assert metrics["denominator"] == 0
    assert "não há taxa de conversão a calcular" in " ".join(metrics["limitations"])


def test_small_sample_is_flagged_not_hidden(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    seed(pipe, "tributario", won=2, lost=0)
    metrics = compute_metrics(pipe.opportunities(), "tributario", **PERIOD)
    assert metrics["win_rate"] == 1.0
    assert metrics["sample_sufficient"] is False
    assert "amostra insuficiente" in " ".join(metrics["limitations"])


def test_sufficient_sample_passes(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    seed(pipe, "tributario", won=5, lost=5)
    metrics = compute_metrics(pipe.opportunities(), "tributario", **PERIOD)
    assert metrics["denominator"] == 10 >= MINIMUM_SAMPLE
    assert metrics["sample_sufficient"] is True
    assert metrics["win_rate"] == 0.5


def test_revenue_counts_only_registered_values(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    seed(pipe, "tributario", won=3)
    metrics = compute_metrics(pipe.opportunities(), "tributario", **PERIOD)
    assert metrics["revenue_brl"] == 30_000.0
    assert metrics["average_ticket_brl"] == 10_000.0


def test_lost_reasons_are_counted(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    seed(pipe, "tributario", lost=3)
    metrics = compute_metrics(pipe.opportunities(), "tributario", **PERIOD)
    assert metrics["lost_reasons"] == {"preco": 3}


# --------------------------------------------------------------- ranking


def test_small_sample_niche_is_physically_separated(tmp_path: Path) -> None:
    """O nicho de 2-de-2 não pode aparecer acima do de 5-de-10 numa lista só."""
    pipe = pipeline(tmp_path)
    seed(pipe, "tributario", won=2)  # 100%, amostra 2
    seed(pipe, "trabalhista", won=5, lost=5)  # 50%, amostra 10
    ranking = rank_niches(pipe.opportunities(), ["tributario", "trabalhista"], by="win_rate", **PERIOD)
    ranked_ids = [m["niche_id"] for m in ranking["ranked"]]
    insufficient_ids = [m["niche_id"] for m in ranking["insufficient_sample"]]
    assert ranked_ids == ["trabalhista"]
    assert "tributario" in insufficient_ids


def test_ranking_orders_by_criterion(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    seed(pipe, "tributario", won=8, lost=2)  # 80%
    seed(pipe, "trabalhista", won=5, lost=5)  # 50%
    ranking = rank_niches(pipe.opportunities(), ["tributario", "trabalhista"], by="win_rate", **PERIOD)
    assert [m["niche_id"] for m in ranking["ranked"]] == ["tributario", "trabalhista"]


def test_unknown_criterion_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="desconhecido"):
        rank_niches(pipeline(tmp_path).opportunities(), ["tributario"], by="follower_count", **PERIOD)


def test_every_metric_carries_limitations(tmp_path: Path) -> None:
    pipe = pipeline(tmp_path)
    seed(pipe, "tributario", won=9, lost=1)
    metrics = compute_metrics(pipe.opportunities(), "tributario", **PERIOD)
    assert metrics["limitations"], "toda métrica declara ao menos uma limitação"
    assert metrics["claim_class"] == "DERIVED_METRIC"


# ------------------------------------------- confronto declarado vs. medido


def test_every_niche_declares_priority_and_ticket_band() -> None:
    for niche in load_niches():
        assert niche["priority"] in {"core", "exploratorio", "legado"}
        assert niche["ticket_band_declared"] in {"baixo", "medio", "alto"}


def test_declared_expectation_is_confirmed_when_data_agrees(tmp_path: Path) -> None:
    from asus_theye.commercial import compute_metrics as cm
    from asus_theye.commercial import reality_check

    pipe = pipeline(tmp_path)
    for index in range(10):  # ticket 120k = faixa alta, como tributario declara
        opportunity = pipe.add(
            new_opportunity(niche_id="tributario", client_identifier=f"e{index}", source_channel="indicacao")
        )
        pipe.advance(opportunity["opportunity_id"], "qualificacao")
        pipe.advance(opportunity["opportunity_id"], "proposta")
        pipe.advance(opportunity["opportunity_id"], "ganho", value_brl=120_000.0)
    check = reality_check(cm(pipe.opportunities(), "tributario", **PERIOD), niche_by_id("tributario"))
    assert check["ticket_band_declared"] == "alto"
    assert check["ticket_band_observed"] == "alto"
    assert check["verdict"] == "confirmed"


def test_declared_expectation_is_contradicted_when_data_disagrees(tmp_path: Path) -> None:
    """O achado mais útil do painel: você achava alto, os dados dizem baixo."""
    from asus_theye.commercial import compute_metrics as cm
    from asus_theye.commercial import reality_check

    pipe = pipeline(tmp_path)
    for index in range(10):  # ticket 9k = faixa baixa, mas tributario declara alto
        opportunity = pipe.add(
            new_opportunity(niche_id="tributario", client_identifier=f"e{index}", source_channel="indicacao")
        )
        pipe.advance(opportunity["opportunity_id"], "qualificacao")
        pipe.advance(opportunity["opportunity_id"], "proposta")
        pipe.advance(opportunity["opportunity_id"], "ganho", value_brl=9_000.0)
    check = reality_check(cm(pipe.opportunities(), "tributario", **PERIOD), niche_by_id("tributario"))
    assert check["verdict"] == "contradicted"
    assert "declarou ticket 'alto'" in check["note"]


def test_small_sample_cannot_contradict_the_expectation(tmp_path: Path) -> None:
    """A hipótese sobrevive por falta de prova, não por estar certa."""
    from asus_theye.commercial import compute_metrics as cm
    from asus_theye.commercial import reality_check

    pipe = pipeline(tmp_path)
    opportunity = pipe.add(new_opportunity(niche_id="tributario", client_identifier="e0", source_channel="site"))
    pipe.advance(opportunity["opportunity_id"], "qualificacao")
    pipe.advance(opportunity["opportunity_id"], "proposta")
    pipe.advance(opportunity["opportunity_id"], "ganho", value_brl=1_000.0)
    check = reality_check(cm(pipe.opportunities(), "tributario", **PERIOD), niche_by_id("tributario"))
    assert check["verdict"] == "insufficient_evidence"


def test_no_data_yields_no_verdict(tmp_path: Path) -> None:
    from asus_theye.commercial import compute_metrics as cm
    from asus_theye.commercial import reality_check

    check = reality_check(cm(pipeline(tmp_path).opportunities(), "tributario", **PERIOD), niche_by_id("tributario"))
    assert check["verdict"] == "no_data"
