# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do painel /mlops."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from asus_theye.dashboard.mlops import mlops_page, register_mlops_routes

# ---------------------------------------------------------------------------
# helpers


def _escrever_jsonl(caminho: Path, linhas: list[dict[str, Any]]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        "\n".join(json.dumps(d) for d in linhas) + "\n",
        encoding="utf-8",
    )


def _stores_sinteticos(base: Path) -> None:
    """Escreve um conjunto mínimo de stores para cobrir todos os painéis."""
    _escrever_jsonl(
        base / "modelos.jsonl",
        [{"modelo_id": "brier-voto", "nome": "Brier Voto", "area": "legislativo", "objetivo": "prev. votos"}],
    )
    _escrever_jsonl(
        base / "versoes.jsonl",
        [{"modelo_id": "brier-voto", "versao": "v1", "origem": "experimento-local"}],
    )
    _escrever_jsonl(
        base / "corridas.jsonl",
        [
            {
                "modelo_id": "brier-voto",
                "versao": "v1",
                "params": {"lr": 0.01, "epochs": 10},
                "metricas": {"brier": 0.003, "acuracia": 0.95},
                "artefatos": ["model.pkl"],
            }
        ],
    )
    _escrever_jsonl(
        base / "promocoes.jsonl",
        [
            {
                "modelo_id": "brier-voto",
                "versao": "v1",
                "papel": "campeao",
                "acoplado_a": "api-voto",
                "promovido_em": "2025-01-01",
            },
            {
                "modelo_id": "brier-voto",
                "versao": "v0",
                "papel": "desafiante",
                "acoplado_a": "api-voto",
                "promovido_em": "2024-12-01",
            },
        ],
    )


# ---------------------------------------------------------------------------
# testes de conteúdo


def test_mlops_page_com_stores_sinteticos(tmp_path: Path) -> None:
    """Página gerada com stores sintéticos deve conter os marcadores esperados."""
    _stores_sinteticos(tmp_path)
    pagina = mlops_page(base=tmp_path)

    assert "<!doctype html>" in pagina.lower()
    assert "MLOPS" in pagina
    # cards
    assert "Modelos" in pagina
    assert "Versões" in pagina
    assert "Corridas" in pagina
    assert "Promoções" in pagina
    # tabela de corridas
    assert "brier-voto@v1" in pagina
    assert "lr=0.01" in pagina or "lr" in pagina
    assert "brier=0.003" in pagina or "brier" in pagina
    # campeão/desafiante
    assert "Brier Voto" in pagina
    assert "campeão" in pagina or "campeao" in pagina.lower()
    # aviso obrigatório no rodapé
    assert "desafiante não tem peso em nada" in pagina
    assert "promoção a influência exige a porta declarada na promoção" in pagina


def test_mlops_page_estado_vazio_honesto(tmp_path: Path) -> None:
    """Sem stores, a página mostra estado vazio sem fingir dado."""
    pagina = mlops_page(base=tmp_path)

    assert "<!doctype html>" in pagina.lower()
    assert "MLOPS" in pagina
    # cards devem existir com zero
    assert "Modelos" in pagina
    assert "Corridas" in pagina
    # mensagens de estado vazio
    assert "nenhuma corrida registrada" in pagina
    # aviso sempre presente
    assert "desafiante não tem peso em nada" in pagina


def test_mlops_page_artefatos_contados(tmp_path: Path) -> None:
    """O número de artefatos deve ser contado corretamente."""
    _escrever_jsonl(
        tmp_path / "modelos.jsonl",
        [{"modelo_id": "m1", "nome": "M1", "area": "a", "objetivo": "o"}],
    )
    _escrever_jsonl(
        tmp_path / "versoes.jsonl",
        [{"modelo_id": "m1", "versao": "v1", "origem": "x"}],
    )
    _escrever_jsonl(
        tmp_path / "corridas.jsonl",
        [
            {
                "modelo_id": "m1",
                "versao": "v1",
                "params": {},
                "metricas": {},
                "artefatos": ["a.pkl", "b.pkl", "c.pkl"],
            }
        ],
    )
    pagina = mlops_page(base=tmp_path)
    assert ">3<" in pagina


# ---------------------------------------------------------------------------
# teste de rota


def test_rota_mlops_montada_no_app(tmp_path: Path) -> None:
    """GET /mlops deve devolver HTML 200 via TestClient."""
    fastapi = pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient  # type: ignore[import-untyped]

    app = fastapi.FastAPI()
    register_mlops_routes(app, base=tmp_path)
    client = TestClient(app)
    resposta = client.get("/mlops")
    assert resposta.status_code == 200
    assert "MLOPS" in resposta.text
    assert "<!doctype html>" in resposta.text.lower()


# ---------------------------------------------------------------------------
# teste de export estático


def test_export_inclui_mlops_html(tmp_path: Path) -> None:
    """exportar() deve incluir mlops.html no conjunto de gerados."""
    from asus_theye.dashboard.export_static import exportar

    resultado = exportar(tmp_path)
    assert "mlops.html" in resultado["gerados"]
    html_gerado = (tmp_path / "mlops.html").read_text(encoding="utf-8")
    assert "MLOPS" in html_gerado
    assert "<!doctype html>" in html_gerado.lower()
