# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do painel de mercados do dashboard.

O render (``markets_page``) é dependency-light e testado sem FastAPI, com um
DuckDB sintético. A rota (``GET /markets``) só é testada se FastAPI estiver
instalado (extra ``dashboard``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from asus_theye.dashboard import markets_page

duckdb = pytest.importorskip("duckdb")


def _tiny_db(path: Path) -> None:
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
    p, o = 0.30, 1
    brier = round((p - o) ** 2, 8)
    con.execute(
        "insert into mercados values (?,?,?,?,?,?,?,?,?,?)",
        ["JUROS-01", "juros", "ETI", "?", "2026-07-01T00:00:00Z", "2026-07-14", "BCB", "c", 0.5, "LIQUIDADO"],
    )
    con.execute(
        "insert into resolucoes values (?,?,?,?,?,?,?)",
        ["JUROS-01", "2026-07-20T00:00:00Z", o, 0.0, brier, 1, "BCB"],
    )
    con.close()


def test_pagina_renderiza_reconciliacao_e_skill(tmp_path: Path) -> None:
    db = tmp_path / "mini.duckdb"
    _tiny_db(db)
    page = markets_page(str(db))
    assert "MERCADOS PREDITIVOS" in page
    assert "Liquidados" in page and ">1<" in page  # 1 liquidado
    assert "juros" in page
    assert "indefinida" in page  # desfecho constante -> skill indefinida
    assert "<!doctype html>" in page.lower()


def test_estado_vazio_quando_banco_ausente(tmp_path: Path) -> None:
    page = markets_page(str(tmp_path / "nao_existe.duckdb"))
    assert "indisponível" in page
    assert "ASUS_MARKETS_DB" in page
    # não pode vazar traceback nem quebrar
    assert "<!doctype html>" in page.lower()


def test_rota_get_markets() -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from asus_theye.dashboard import create_dashboard_app

    app = create_dashboard_app(markets_db="/caminho/inexistente/x.duckdb")
    client = TestClient(app)
    response = client.get("/markets")
    assert response.status_code == 200
    assert "MERCADOS PREDITIVOS" in response.text
    assert "indisponível" in response.text  # degrada com banco ausente, sem 500
