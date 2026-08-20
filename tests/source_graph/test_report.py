# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes dos três relatórios da Fase C.

O que se protege aqui é o que os relatórios NÃO podem esconder: um zero sem
motivo, uma lacuna sem saída declarada, ou uma limitação omitida.
"""

from __future__ import annotations

from asus_theye.source_graph.coverage import build_coverage, coverage_by_track
from asus_theye.source_graph.report import (
    coverage_report,
    gaps_report,
    limitations_report,
    write_reports,
)

COVERAGE = build_coverage([])
TRACKS = coverage_by_track(COVERAGE)


def test_coverage_report_names_every_track_and_category() -> None:
    text = coverage_report(COVERAGE, TRACKS)
    assert "Cobertura do grafo de fontes" in text
    for track in TRACKS:
        assert track in text
    for entry in COVERAGE["by_category"]:
        assert entry["category_id"] in text


def test_coverage_report_carries_the_snapshot_hash() -> None:
    """Sem o hash, o relatório é uma afirmação sem prova."""
    assert COVERAGE["snapshot_hash_sha256"][:16] in coverage_report(COVERAGE, TRACKS)


def test_gaps_report_declares_a_way_out_for_every_gap() -> None:
    text = gaps_report(COVERAGE)
    for gap in COVERAGE["gaps"]:
        assert gap["description"] in text
        assert gap["what_would_unblock"] in text


def test_limitations_report_states_what_the_numbers_do_not_mean() -> None:
    text = limitations_report(COVERAGE)
    for claim in (
        "omitido, nunca zerado",
        "não são preenchidas",
        "Pessoas não são ranqueadas",
        "métrica social",
    ):
        assert claim in text


def test_limitations_report_admits_nothing_was_fetched_yet() -> None:
    assert "Nenhuma busca foi executada" in limitations_report(COVERAGE)


def test_reason_labels_are_translated_not_leaked_raw() -> None:
    """O leitor vê 'exige DPIA humana', não 'requires_dpia'."""
    text = coverage_report(COVERAGE, TRACKS)
    assert "exige DPIA humana" in text or "ainda não tentado" in text


def test_write_reports_creates_the_three_phase_c_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("asus_theye.source_graph.report.REPORTS_DIR", tmp_path)
    written = write_reports(COVERAGE, TRACKS)
    names = {path.name for path in written}
    assert names == {
        "LEGAL_SOURCE_COVERAGE.md",
        "SOURCE_GAPS.md",
        "RANKING_LIMITATIONS.md",
    }
    for path in written:
        assert path.exists()
        assert path.read_text(encoding="utf-8").startswith("# ")
