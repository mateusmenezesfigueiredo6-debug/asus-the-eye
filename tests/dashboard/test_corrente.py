# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do painel /corrente — extrato navegável da cadeia auditável."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.audit.schema import GENESIS_HASH, seal_event
from asus_theye.dashboard.corrente import corrente_page
from asus_theye.dashboard.export_static import exportar


def _evento(
    sequence: int,
    previous_hash: str,
    event_type: str,
    occurred_at: str,
    *,
    content: str,
) -> dict[str, object]:
    return seal_event(
        {
            "schema_version": "1.0.0",
            "event_id": f"ev-{sequence}",
            "idempotency_key": f"idem-{sequence:04d}",
            "tenant_id": "tenant-demo",
            "sequence": sequence,
            "event_type": event_type,
            "action": "record",
            "occurred_at": occurred_at,
            "recorded_at": occurred_at,
            "actor_type": "system",
            "actor_id_pseudonymous": "svc-dashboard",
            "actor_role": "worker",
            "source_system": "tests",
            "resource_type": "market",
            "resource_id_pseudonymous": f"claim-{sequence:04d}",
            "resource_version": str(sequence),
            "jurisdiction": "BR",
            "legal_area_ids": ["technology-data-and-cyber"],
            "classification": "public",
            "retention_policy_id": "rp-public",
            "lawful_basis_reference": "teste",
            "content_hash_sha256": "1" * 64,
            "metadata_hash_sha256": "2" * 64,
            "previous_event_hash_sha256": previous_hash,
            "correlation_id": f"corr-{sequence:04d}",
            "causation_id": f"cause-{sequence:04d}",
            "model_provider": "none",
            "model_name": "none",
            "model_version": "0",
            "prompt_template_version": "0",
            "source_citation_hashes": [],
            "human_review_status": "not_required",
            "reviewer_pseudonymous": "reviewer",
            "result_status": "ok",
            "error_code": "",
            "created_by_service": "tests",
            "build_version": "test",
            "content": content,
        }
    )


def _base_com_corrente(tmp_path: Path, *, total_eventos: int = 55) -> Path:
    base = tmp_path / "markets"
    base.mkdir(parents=True)
    linhas: list[dict[str, object]] = []
    previous = GENESIS_HASH
    tipos = ["market.settlement", "market.comparator", "project.measurement", "ml.run"]
    for sequence in range(1, total_eventos + 1):
        evento = _evento(
            sequence,
            previous,
            tipos[(sequence - 1) % len(tipos)],
            f"2026-08-{(sequence % 28) + 1:02d}T12:00:00Z",
            content=f"SEGREDO-{sequence}",
        )
        previous = str(evento["event_hash_sha256"])
        linhas.append(evento)
    (base / "eventos.jsonl").write_text(
        "\n".join(json.dumps(linha, ensure_ascii=False) for linha in linhas) + "\n",
        encoding="utf-8",
    )
    (base / "ancoras.jsonl").write_text(
        json.dumps(
            {
                "manifest": {
                    "tenant_id": "tenant-demo",
                    "batch_id": "batch-1",
                    "first_sequence": 1,
                    "last_sequence": total_eventos - 1,
                },
                "ancora": {"tx_hash": "0x" + "a" * 64, "chain_id": 84532, "contrato": "0x" + "b" * 40},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return base


def test_pagina_mostra_extrato_dos_ultimos_50_sem_vazar_conteudo(tmp_path: Path) -> None:
    page = corrente_page(_base_com_corrente(tmp_path))
    assert "CORRENTE" in page
    assert "55" in page
    assert "verify_chain" in page and "ok" in page
    assert "market.settlement" in page and "liquidação contra fonte oficial" in page
    assert ">55<" in page and ">54<" in page
    assert ">5<" not in page
    assert "ancorada" in page and "sem âncora" in page
    assert "SEGREDO-55" not in page
    assert "conteúdo não sai daqui" in page


def test_corrente_vazia_mostra_estado_honesto(tmp_path: Path) -> None:
    page = corrente_page(tmp_path / "nao-existe")
    assert "Corrente vazia" in page
    assert "0" in page
    assert "nunca o conteúdo dos eventos" in page


def test_rota_corrente_montada_no_app() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from asus_theye.dashboard.app import create_dashboard_app

    resposta = TestClient(create_dashboard_app()).get("/corrente")
    assert resposta.status_code == 200
    assert "CORRENTE" in resposta.text


def test_export_static_inclui_corrente_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)
    resultado = exportar(tmp_path)
    assert "corrente.html" in resultado["gerados"]
    html = (tmp_path / "corrente.html").read_text(encoding="utf-8")
    assert "CORRENTE" in html
