"""Testes do export estático dos painéis do dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.cli import main
from asus_theye.dashboard.export_static import exportar


def test_exportar_gera_html_e_index_e_pula_markets_sem_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)

    destino = tmp_path / "dist"
    resultado = exportar(destino)

    assert (destino / "projeto.html").exists()
    assert (destino / "evidencia.html").exists()
    assert (destino / "benchmark.html").exists()
    assert (destino / "index.html").exists()
    assert not (destino / "markets.html").exists()
    assert "MEDIÇÃO DO PROJETO" in (destino / "projeto.html").read_text(encoding="utf-8")
    assert "EVIDÊNCIA" in (destino / "evidencia.html").read_text(encoding="utf-8")
    assert "ASUS THE EYE BENCHMARK" in (destino / "benchmark.html").read_text(encoding="utf-8")
    index = (destino / "index.html").read_text(encoding="utf-8")
    assert 'href="projeto.html"' in index
    assert 'href="evidencia.html"' in index
    assert 'href="benchmark.html"' in index
    assert 'href="markets.html"' not in index
    assert any("markets.html" in item for item in resultado["pulados"])


def test_cli_export_static_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)

    destino = tmp_path / "saida"
    code = main(["export-static", "--out", str(destino), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert str(destino / "index.html") in payload["gerados"]
    assert any("markets.html" in item for item in payload["pulados"])
