# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do painel dos mercados vivos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_pagina_real_mostra_os_tres_mercados() -> None:
    """O painel real, sem observação de comparador.

    A divergência que este teste afirmava saía do preço da Kalshi e
    foi expurgada (``data.redaction``, termos de terceiro). O painel degrada
    honestamente: mostra os mercados e continua declarando a doutrina, sem
    inventar um número de comparador que não existe mais.
    """
    from asus_theye.dashboard.mercados import mercados_page

    page = mercados_page()  # estado REAL do repo
    for marca in ("MACRO-01::2026-08", "JUROS-01::2026-09", "CAMBIO-01::2026-09", "comparador, nunca fonte"):
        assert marca in page, f"marca ausente: {marca}"
    assert "retrospectivas" in page.lower()  # a exclusão honesta é dita


def test_probabilidade_carrega_proveniencia(tmp_path: Path) -> None:
    from asus_theye.dashboard.mercados import mercados_page

    base = tmp_path
    registro = {
        "versao": 1,
        "mercados": [
            {
                "claim_id": "X::2026-09",
                "market_area_id": "macroeconomia",
                "question": "P?",
                "deadline": "2026-09-30",
                "probability": 0.8333,
                "resolution_source": "f",
                "created_at": "t",
                "mes_referencia": "2026-09",
                "limiar": 0.5,
                "criterio": "c",
                "serie_sgs": 433,
                "estado": "ABERTO",
                "tentativas": [],
                "gerador": {"fontes": ["BCB Focus"], "valor": 0.8333},
            },
            {
                "claim_id": "Y::2026-09",
                "market_area_id": "juros",
                "question": "Q?",
                "deadline": "2026-09-30",
                "probability": 0.5,
                "resolution_source": "f",
                "created_at": "t",
                "mes_referencia": "2026-09",
                "limiar": 14.0,
                "criterio": "c",
                "serie_sgs": 432,
                "estado": "ABERTO",
                "tentativas": [],
            },
        ],
    }
    (base / "registro.json").write_text(json.dumps(registro), encoding="utf-8")
    page = mercados_page(base)
    assert "WPAM" in page and "BCB Focus" in page  # proveniência visível
    assert "prior declarado" in page  # sem sinal = dito como tal


def test_registro_vazio_e_honesto(tmp_path: Path) -> None:
    from asus_theye.dashboard.mercados import mercados_page

    page = mercados_page(tmp_path)
    assert "nenhum" in page and "markets-emitir" in page


def test_rota_montada_no_app() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from asus_theye.dashboard.app import create_dashboard_app

    resposta = TestClient(create_dashboard_app()).get("/mercados")
    assert resposta.status_code == 200 and "MERCADOS" in resposta.text
