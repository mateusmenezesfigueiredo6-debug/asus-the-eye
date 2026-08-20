# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do Mistress Chart: build, render e hash."""

from __future__ import annotations

from typing import Any

from asus_theye.chart import build_chart, chart_snapshot_hash, render_html, render_text


def _snapshot_minimo() -> dict[str, Any]:
    """Snapshot sintético com campos obrigatórios; não depende de dados do repo."""
    return {
        "commit": "abc1234",
        "generated_at": "2026-01-01T00:00:00Z",
        "totals": {
            "projects": 1,
            "projects_complete": 0,
            "tests": 0,
            "niches_covered": 0,
            "niches_total": 1,
            "niche_coverage_pct": 0,
        },
        "ledger": {"events": 0, "head_sequence": 0, "event_types": {}},
        "pipeline": {},
        "projects": [],
        "group_coverage": {},
        "knowledge": {},
    }


# -------------------------------------------------------- build_chart


def test_build_chart_devolve_chaves_obrigatorias() -> None:
    snapshot = build_chart()
    for chave in ("commit", "generated_at", "totals", "ledger", "projects", "pipeline"):
        assert chave in snapshot, f"chave obrigatória ausente: {chave!r}"


def test_build_chart_totals_nao_negativos() -> None:
    snapshot = build_chart()
    totals = snapshot["totals"]
    assert totals["projects"] >= 0
    assert totals["niches_covered"] >= 0
    assert totals["niches_total"] >= 0


# -------------------------------------------------------- chart_snapshot_hash


def test_chart_snapshot_hash_e_hex_sha256() -> None:
    snapshot = _snapshot_minimo()
    h = chart_snapshot_hash(snapshot)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_chart_snapshot_hash_e_determinista() -> None:
    snapshot = _snapshot_minimo()
    assert chart_snapshot_hash(snapshot) == chart_snapshot_hash(snapshot)


def test_chart_snapshot_hash_muda_com_conteudo() -> None:
    s1 = _snapshot_minimo()
    s2 = {**_snapshot_minimo(), "commit": "outro"}
    assert chart_snapshot_hash(s1) != chart_snapshot_hash(s2)


# -------------------------------------------------------- render_text


def test_render_text_contem_cabecalho_e_hash() -> None:
    snapshot = _snapshot_minimo()
    h = chart_snapshot_hash(snapshot)
    texto = render_text(snapshot, h)
    assert "MISTRESS CHART" in texto
    assert h in texto


def test_render_text_e_string_nao_vazia() -> None:
    snapshot = build_chart()
    h = chart_snapshot_hash(snapshot)
    texto = render_text(snapshot, h)
    assert isinstance(texto, str) and len(texto) > 0


# -------------------------------------------------------- render_html


def test_render_html_produz_doctype() -> None:
    snapshot = _snapshot_minimo()
    h = chart_snapshot_hash(snapshot)
    html_out = render_html(snapshot, h)
    assert "<!DOCTYPE html>" in html_out or "<html" in html_out


def test_render_html_nao_contem_script_executavel() -> None:
    snapshot = build_chart()
    h = chart_snapshot_hash(snapshot)
    html_out = render_html(snapshot, h)
    assert "<script" not in html_out.lower()


def test_render_html_contem_hash() -> None:
    snapshot = _snapshot_minimo()
    h = chart_snapshot_hash(snapshot)
    html_out = render_html(snapshot, h)
    assert h in html_out
