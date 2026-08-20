# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do subcomando ``asus-theye markets-reconcile``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.cli import main

duckdb = pytest.importorskip("duckdb")


def _tiny_db(path: Path) -> None:
    """asus_teste.duckdb minúsculo: 1 contrato liquidado com brier exato."""
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
        [
            "JUROS-01",
            "juros",
            "ETI",
            "?",
            "2026-07-01T00:00:00Z",
            "2026-07-14",
            "Banco Central do Brasil",
            "criterio",
            0.5,
            "LIQUIDADO",
        ],
    )
    con.execute(
        "insert into resolucoes values (?,?,?,?,?,?,?)",
        ["JUROS-01", "2026-07-20T00:00:00Z", o, 0.0, brier, 1, "Banco Central do Brasil"],
    )
    con.close()


def test_reconcile_tabela(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "mini.duckdb"
    _tiny_db(db)
    code = main(["markets-reconcile", "--db", str(db)])
    out = capsys.readouterr().out
    assert "RECONCILIAÇÃO CONTRA O BANCO MEDIDO" in out
    assert "liquidados: 1" in out
    assert "juros" in out
    # per-contract bate; o agregado não tem publicado no classificador p/ 'juros'
    # (área aberta, brier null), então tie_out é False -> código 1.
    assert code == 1


def test_reconcile_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "mini.duckdb"
    _tiny_db(db)
    code = main(["markets-reconcile", "--db", str(db), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["settled_total"] == 1
    assert payload["areas"][0]["per_contract_matches"] is True
    assert code in (0, 1)


def test_reconcile_banco_ausente(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["markets-reconcile", "--db", str(tmp_path / "nao_existe.duckdb")])
    out = capsys.readouterr().out
    assert "markets-reconcile:" in out
    assert code == 1


def test_reconcile_com_skill(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "mini.duckdb"
    _tiny_db(db)
    main(["markets-reconcile", "--db", str(db), "--skill"])
    out = capsys.readouterr().out
    assert "SKILL vs baseline" in out
    assert "juros" in out
    # desfecho único = 1 -> taxa-base perfeita -> skill indefinida, baseline vence
    assert "indefinida" in out


def test_reconcile_skill_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "mini.duckdb"
    _tiny_db(db)
    main(["markets-reconcile", "--db", str(db), "--skill", "--baseline", "0.7", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "skill" in payload
    juros = next(a for a in payload["skill"]["areas"] if a["area_id"] == "juros")
    assert juros["baseline_probability"] == 0.7
