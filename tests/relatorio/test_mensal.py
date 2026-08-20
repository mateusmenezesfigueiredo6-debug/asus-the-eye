# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do extrato mensal em Markdown."""

from __future__ import annotations

import json
from pathlib import Path

from asus_theye.cli import main
from asus_theye.relatorio import relatorio_mensal


def _escrever_json(caminho: Path, dado: object) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _escrever_jsonl(caminho: Path, linhas: list[dict[str, object]]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(json.dumps(linha, ensure_ascii=False) for linha in linhas) + "\n", encoding="utf-8")


def _popular_base(base: Path) -> None:
    _escrever_json(
        base / "projeto" / "fases.json",
        {
            "fases": [
                {"id": "F0", "nome": "ingestão", "estado": "feito", "peso_concluido": 1.0, "metodo": "sintético"},
                {"id": "F1", "nome": "evidência", "estado": "parcial", "peso_concluido": 0.5, "metodo": "sintético"},
            ]
        },
    )
    _escrever_json(
        base / "markets" / "registro.json",
        {
            "versao": 1,
            "mercados": [
                {
                    "claim_id": "MACRO-01::2026-08",
                    "market_area_id": "macroeconomia",
                    "question": "IPCA agosto >= 0,50%?",
                    "deadline": "2026-08-31",
                    "probability": 0.55,
                    "created_at": "2026-08-01T00:00:00Z",
                    "mes_referencia": "2026-08",
                    "limiar": 0.5,
                    "criterio": "IPCA mensal >= 0.50%",
                    "serie_sgs": 433,
                    "estado": "ABERTO",
                    "tentativas": [],
                },
                {
                    "claim_id": "MACRO-01::2026-07",
                    "market_area_id": "macroeconomia",
                    "question": "IPCA julho >= 0,50%?",
                    "deadline": "2026-07-31",
                    "probability": 0.5,
                    "created_at": "2026-07-01T00:00:00Z",
                    "mes_referencia": "2026-07",
                    "limiar": 0.5,
                    "criterio": "IPCA mensal >= 0.50%",
                    "serie_sgs": 433,
                    "estado": "LIQUIDADO",
                    "tentativas": [],
                },
            ],
        },
    )
    _escrever_jsonl(
        base / "markets" / "resolucoes.jsonl",
        [
            {
                "claim_id": "MACRO-01::2026-08",
                "outcome": 1,
                "resolution_source": "api.bcb.gov.br (SGS)",
                "resolved_at": "2026-08-20T10:00:00Z",
                "brier_do_contrato": 0.2025,
            },
            {
                "claim_id": "MACRO-01::2026-07",
                "outcome": 0,
                "resolution_source": "api.bcb.gov.br (SGS)",
                "resolved_at": "2026-07-20T10:00:00Z",
                "brier_do_contrato": 0.2500,
            },
        ],
    )
    _escrever_jsonl(
        base / "markets" / "comparador.jsonl",
        [
            {
                "claim_id": "MACRO-01::2026-08",
                "comparator": "Kalshi",
                "comparator_price": 0.62,
                "our_probability": 0.55,
                "divergence": 0.07,
                "ticker": "KXCPI-26AUG",
                "recorded_at": "2026-08-19T12:00:00Z",
            },
            {
                "claim_id": "MACRO-01::2026-09",
                "comparator": "Kalshi",
                "comparator_price": 0.48,
                "our_probability": 0.51,
                "divergence": 0.03,
                "ticker": "KXCPI-26SEP",
                "recorded_at": "2026-09-01T12:00:00Z",
            },
        ],
    )
    _escrever_jsonl(
        base / "markets" / "eventos.jsonl",
        [
            {
                "sequence": 1,
                "event_type": "market.settlement",
                "correlation_id": "MACRO-01::2026-08",
                "occurred_at": "2026-08-20T10:00:00Z",
                "recorded_at": "2026-08-20T10:00:01Z",
                "event_hash_sha256": "a" * 64,
            },
            {
                "sequence": 2,
                "event_type": "market.settlement",
                "correlation_id": "MACRO-01::2026-09",
                "occurred_at": "2026-09-20T10:00:00Z",
                "recorded_at": "2026-09-20T10:00:01Z",
                "event_hash_sha256": "b" * 64,
            },
        ],
    )
    _escrever_jsonl(
        base / "markets" / "ancoras.jsonl",
        [
            {
                "manifest": {"merkle_root": "c" * 64},
                "ancora": {"tx_hash": "0x" + "d" * 64, "chain_id": 84532},
                "registrado_em": "2026-08-21T00:00:00Z",
            }
        ],
    )
    _escrever_jsonl(
        base / "mlops" / "corridas.jsonl",
        [
            {
                "modelo_id": "brier-voto",
                "versao": "v1",
                "estado": "sucesso",
                "executada_em": "2026-08-03T08:00:00Z",
            }
        ],
    )


def test_relatorio_mensal_com_dados_sinteticos(tmp_path: Path) -> None:
    _popular_base(tmp_path)
    texto = relatorio_mensal("2026-08", base=tmp_path)

    assert "# Relatório mensal da plataforma — 2026-08" in texto
    assert "Mercados emitidos no mês: 1 | liquidações no mês: 1" in texto
    assert "| MACRO-01::2026-08 | 1 | 0.2025 | api.bcb.gov.br (SGS) |" in texto
    assert "| MACRO-01::2026-08 | macroeconomia | ABERTO | 0.5500 | 2026-08-01T00:00:00Z |" in texto
    assert "| MACRO-01::2026-08 | Kalshi | 0.6200 | 0.5500 | 0.0700 | KXCPI-26AUG |" in texto
    assert "© 2026 Mateus Menezes Figueiredo · AGPL-3.0" in texto


def test_relatorio_mensal_mes_vazio_diz_nenhum(tmp_path: Path) -> None:
    texto = relatorio_mensal("2026-08", base=tmp_path)

    assert "Mercados emitidos no mês: 0 | liquidações no mês: 0" in texto
    assert texto.count("\nnenhum\n") >= 6
    assert "© 2026 Mateus Menezes Figueiredo · AGPL-3.0" in texto


def test_relatorio_mensal_filtra_o_mes_certo(tmp_path: Path) -> None:
    _popular_base(tmp_path)
    texto = relatorio_mensal("2026-08", base=tmp_path)

    assert "MACRO-01::2026-08" in texto
    assert "MACRO-01::2026-09" not in texto
    assert "| 2 | market.settlement |" not in texto


def test_cli_relatorio_mensal_escreve_arquivo(tmp_path: Path, monkeypatch) -> None:
    _popular_base(tmp_path / "reports")
    saida = tmp_path / "mensal.md"
    monkeypatch.chdir(tmp_path)

    code = main(["relatorio-mensal", "--mes", "2026-08", "--saida", str(saida)])

    assert code == 0
    assert saida.exists()
    assert "Relatório mensal da plataforma" in saida.read_text(encoding="utf-8")
