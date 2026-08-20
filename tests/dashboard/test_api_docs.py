"""Testes do painel /api e da documentação da API pública do verificador."""

from __future__ import annotations

from pathlib import Path

import pytest

from asus_theye.dashboard.api_docs import api_docs_page
from asus_theye.dashboard.export_static import exportar


def test_api_docs_page_marcadores_obrigatorios() -> None:
    page = api_docs_page()
    assert "<!doctype html>" in page.lower()
    assert "API PÚBLICA — verificador" in page
    assert "GET /health" in page
    assert "POST /verify" in page
    assert "GET /root/AAAA-MM-DD" in page
    assert "nada é persistido" in page
    assert "não revela" in page.lower()


def test_rota_get_api() -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient  # type: ignore[import-untyped]

    from asus_theye.dashboard import create_dashboard_app

    app = create_dashboard_app()
    client = TestClient(app)
    resposta = client.get("/api")
    assert resposta.status_code == 200
    assert "POST /verify" in resposta.text


def test_export_inclui_api_html(tmp_path: Path) -> None:
    resultado = exportar(tmp_path)
    assert "api.html" in resultado["gerados"]
    html = (tmp_path / "api.html").read_text(encoding="utf-8")
    assert "GET /root/AAAA-MM-DD" in html
