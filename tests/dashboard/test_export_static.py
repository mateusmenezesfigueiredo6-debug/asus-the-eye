# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do subcomando export-static e do módulo export_static."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.dashboard.export_static import exportar


def test_exportar_gera_html_basico(tmp_path: Path) -> None:
    """Painéis base devem ser gerados sem ASUS_MARKETS_DB; markets é pulado."""
    resultado = exportar(tmp_path)
    assert set(resultado["gerados"]) == {
        "projeto.html",
        "evidencia.html",
        "calibracao.html",
        "corrente.html",
        "benchmark.html",
        "mercados.html",
        "mlops.html",
        "api.html",
        "index.html",
    }
    assert len(resultado["pulados"]) == 1
    assert "markets" in resultado["pulados"][0]


def test_exportar_conteudo_projeto(tmp_path: Path) -> None:
    exportar(tmp_path)
    html = (tmp_path / "projeto.html").read_text(encoding="utf-8")
    assert "MEDIÇÃO DO PROJETO" in html
    assert "<!doctype html>" in html.lower()


def test_exportar_conteudo_evidencia(tmp_path: Path) -> None:
    exportar(tmp_path)
    html = (tmp_path / "evidencia.html").read_text(encoding="utf-8")
    assert "EVIDÊNCIA" in html
    assert "<!doctype html>" in html.lower()


def test_exportar_conteudo_benchmark(tmp_path: Path) -> None:
    exportar(tmp_path)
    html = (tmp_path / "benchmark.html").read_text(encoding="utf-8")
    assert "BENCHMARK" in html
    assert "<svg" in html
    assert "<script>" not in html
    assert "<!doctype html>" in html.lower()


def test_exportar_index_tem_links(tmp_path: Path) -> None:
    exportar(tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "projeto.html" in html
    assert "evidencia.html" in html
    assert "corrente.html" in html
    assert "benchmark.html" in html
    assert "api.html" in html
    assert "<!doctype html>" in html.lower()


def test_exportar_markets_com_db_ausente_listado_em_pulados(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)
    resultado = exportar(tmp_path)
    assert any("markets" in p for p in resultado["pulados"])
    assert not (tmp_path / "markets.html").exists()


def test_exportar_markets_com_db_existente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    duckdb = pytest.importorskip("duckdb")

    db = tmp_path / "mini.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "create table mercados (id varchar, produto varchar, etiqueta varchar, "
        "pergunta_leiga varchar, data_abertura varchar, data_limite varchar, "
        "fonte_resolucao varchar, criterio_resolucao varchar, limiar double, status varchar)"
    )
    con.execute(
        "create table resolucoes (mercado_id varchar, timestamp varchar, resultado_real integer, "
        "valor_observado double, brier_do_contrato double, acerto integer, fonte_confirmacao varchar)"
    )
    con.close()

    monkeypatch.setenv("ASUS_MARKETS_DB", str(db))
    resultado = exportar(tmp_path)
    assert "markets.html" in resultado["gerados"]
    assert all("markets" not in p for p in resultado["pulados"])
    html = (tmp_path / "markets.html").read_text(encoding="utf-8")
    assert "MERCADOS PREDITIVOS" in html


def test_cli_export_static_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)
    from asus_theye.cli import main

    code = main(["export-static", "--out", str(tmp_path), "--json"])
    assert code == 0


def test_cli_export_static_json_valido(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)
    from asus_theye.cli import main

    main(["export-static", "--out", str(tmp_path), "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "gerados" in data and "pulados" in data


def test_export_inclui_mercados_html(tmp_path, monkeypatch):
    """O painel dos mercados vivos entra no site estático."""
    from asus_theye.dashboard.export_static import exportar

    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)
    resultado = exportar(tmp_path)
    assert "mercados.html" in resultado["gerados"]
    conteudo = (tmp_path / "mercados.html").read_text(encoding="utf-8")
    assert "probabilidade com proveniência" in conteudo or "MERCADOS" in conteudo
