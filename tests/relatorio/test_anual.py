# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do consolidado anual em Markdown."""

from __future__ import annotations

import json
from pathlib import Path

from asus_theye.cli import main
from asus_theye.relatorio import relatorio_anual


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
                    "claim_id": "MACRO-01::2026-01",
                    "market_area_id": "macroeconomia",
                    "probability": 0.50,
                    "created_at": "2026-01-02T00:00:00Z",
                    "estado": "LIQUIDADO",
                },
                {
                    "claim_id": "MACRO-02::2026-06",
                    "market_area_id": "macroeconomia",
                    "probability": 0.70,
                    "created_at": "2026-06-02T00:00:00Z",
                    "estado": "LIQUIDADO",
                },
                {
                    "claim_id": "JUROS-01::2026-09",
                    "market_area_id": "juros",
                    "probability": 0.60,
                    "created_at": "2026-09-02T00:00:00Z",
                    "estado": "LIQUIDADO",
                },
                {
                    "claim_id": "LEGADO-01::2026",
                    "market_area_id": "cambio",
                    "probability": 0.90,
                    "created_at": "2026-07-25T06:22:59Z",
                    "estado": "LIQUIDADO",
                },
            ],
        },
    )
    _escrever_jsonl(
        base / "markets" / "resolucoes.jsonl",
        [
            {
                "claim_id": "MACRO-01::2026-01",
                "outcome": 0,
                "resolution_source": "api.bcb.gov.br (SGS)",
                "resolved_at": "2026-02-10T10:00:00Z",
                "brier_do_contrato": 0.25,
            },
            {
                "claim_id": "MACRO-02::2026-06",
                "outcome": 1,
                "resolution_source": "api.bcb.gov.br (SGS)",
                "resolved_at": "2026-07-10T10:00:00Z",
                "brier_do_contrato": 0.09,
            },
            {
                "claim_id": "JUROS-01::2026-09",
                "outcome": 1,
                "resolution_source": "api.bcb.gov.br (Selic)",
                "resolved_at": "2026-09-20T10:00:00Z",
                "brier_do_contrato": 0.16,
            },
            {
                "claim_id": "LEGADO-01::2026",
                "outcome": 1,
                "resolution_source": "PTAX oficial",
                "resolved_at": "2026-07-25T06:24:48Z",
                "brier_do_contrato": 0.01,
            },
        ],
    )
    _escrever_jsonl(
        base / "markets" / "eventos.jsonl",
        [
            {
                "sequence": 1,
                "event_type": "market.settlement",
                "correlation_id": "MACRO-01::2026-01",
                "occurred_at": "2026-02-10T10:00:00Z",
                "recorded_at": "2026-02-10T10:00:01Z",
                "event_hash_sha256": "a" * 64,
            },
            {
                "sequence": 2,
                "event_type": "ml.run",
                "correlation_id": "ml:corrida:1",
                "occurred_at": "2026-09-01T10:00:00Z",
                "recorded_at": "2026-09-01T10:00:01Z",
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
                "registrado_em": "2026-09-21T00:00:00Z",
            }
        ],
    )
    _escrever_jsonl(
        base / "mlops" / "corridas.jsonl",
        [
            {
                "modelo_id": "ipca-nowcast-linear",
                "versao": "v1",
                "estado": "CONCLUIDA",
                "executada_em": "2026-09-03T08:00:00Z",
            }
        ],
    )
    _escrever_jsonl(
        base / "markets" / "legado_retrospectivo.jsonl",
        [
            {
                "claim_id": "LEGADO-01::2026",
                "market_area_id": "cambio",
                "resolved_at": "2026-07-25T06:24:48Z",
                "created_at": "2026-07-25T06:22:59Z",
                "quoted_at": "2026-07-25T06:22:59Z",
                "brier_do_contrato": 0.01,
                "forecast_eligible": False,
                "historical_reconstruction": True,
                "inelegivel_como_previsao": True,
            }
        ],
    )


def test_relatorio_anual_agrega_ano_e_brier_por_area(tmp_path: Path) -> None:
    _popular_base(tmp_path)
    texto = relatorio_anual("2026", base=tmp_path)

    assert "# Relatório anual da plataforma — 2026" in texto
    assert "Mercados emitidos no ano: 3 | liquidações elegíveis no ano: 3" in texto
    assert "Eventos selados: 2 | âncoras: 1 | corridas MLOps: 1" in texto
    assert "| macroeconomia | 2 | 0.1700 | api.bcb.gov.br (SGS) |" in texto
    assert "| juros | 1 | 0.1600 | api.bcb.gov.br (Selic) |" in texto
    assert "© 2026 Mateus Menezes Figueiredo · AGPL-3.0" in texto


def test_relatorio_anual_ano_vazio_permanece_honesto(tmp_path: Path) -> None:
    texto = relatorio_anual("2026", base=tmp_path)

    assert "Mercados emitidos no ano: 0 | liquidações elegíveis no ano: 0" in texto
    assert "## Brier médio por área (somente liquidados elegíveis)\n\nnenhum" in texto
    assert "Nenhuma reconstrução retrospectiva do acervo legado apareceu neste ano." in texto


def test_relatorio_anual_exclui_retrospectivo_e_diz_isso(tmp_path: Path) -> None:
    _popular_base(tmp_path)
    texto = relatorio_anual("2026", base=tmp_path)

    assert "LEGADO-01::2026" not in texto
    assert (
        "1 reconstrução retrospectiva em `reports/markets/legado_retrospectivo.jsonl` ficou fora deste consolidado"
        in texto
    )


def test_relatorio_anual_confere_brier_medio_a_mao(tmp_path: Path) -> None:
    _popular_base(tmp_path)
    texto = relatorio_anual("2026", base=tmp_path)

    assert "| macroeconomia | 2 | 0.1700 |" in texto  # (0.25 + 0.09) / 2 = 0.17


def test_cli_relatorio_anual_escreve_arquivo(tmp_path: Path, monkeypatch) -> None:
    _popular_base(tmp_path / "reports")
    saida = tmp_path / "anual.md"
    monkeypatch.chdir(tmp_path)

    code = main(["relatorio-anual", "--ano", "2026", "--saida", str(saida)])

    assert code == 0
    assert saida.exists()
    assert "Relatório anual da plataforma" in saida.read_text(encoding="utf-8")
