# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do painel /evidencia — linhagem verificável no navegador."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.dashboard.evidencia import evidencia_page

FONTE_BCB = "api.bcb.gov.br (SGS)"


def _base_com_corrente(tmp: Path) -> Path:
    base = tmp / "markets"
    base.mkdir(parents=True)
    (base / "registro.json").write_text(
        json.dumps(
            {
                "versao": 1,
                "mercados": [
                    {
                        "claim_id": "MACRO-01::2026-07",
                        "market_area_id": "macroeconomia",
                        "question": "IPCA jul >= 0,50%?",
                        "probability": 0.5,
                        "resolution_source": FONTE_BCB,
                        "estado": "LIQUIDADO",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (base / "resolucoes.jsonl").write_text(
        json.dumps(
            {"claim_id": "MACRO-01::2026-07", "outcome": 0, "resolution_source": FONTE_BCB, "brier_do_contrato": 0.25}
        )
        + "\n",
        encoding="utf-8",
    )
    (base / "eventos.jsonl").write_text(
        json.dumps(
            {
                "event_id": "ev-1",
                "sequence": 1,
                "event_hash_sha256": "a" * 64,
                "previous_event_hash_sha256": "0" * 64,
                "correlation_id": "MACRO-01::2026-07",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return base


def test_pagina_mostra_linhagem_ate_a_fonte(tmp_path: Path) -> None:
    page = evidencia_page(_base_com_corrente(tmp_path))
    assert "EVIDÊNCIA" in page
    assert "Fonte provada" in page  # a linhagem chega à Fonte
    assert FONTE_BCB in page
    assert "EventoSelado" in page and "Resolucao" in page
    assert "<!doctype html>" in page.lower()


def test_sem_ancora_avisa_parcial_honesto(tmp_path: Path) -> None:
    page = evidencia_page(_base_com_corrente(tmp_path))
    assert "ainda não" in page  # card "Ancorado on-chain"
    assert "PARCIAL" in page  # aviso honesto


def test_corrente_vazia_degrada_sem_estourar(tmp_path: Path) -> None:
    page = evidencia_page(tmp_path / "nao-existe")
    assert "vazia" in page
    assert "markets-resolve" in page  # instrução de como popular


def test_rota_get_evidencia() -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from asus_theye.dashboard import create_dashboard_app

    client = TestClient(create_dashboard_app())
    resposta = client.get("/evidencia")
    assert resposta.status_code == 200
    assert "EVIDÊNCIA" in resposta.text
