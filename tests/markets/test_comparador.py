# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do M4 — divergência vs Kalshi medida e selada (nunca resolutora)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from asus_theye.markets.comparador import ComparadorError, observar_divergencia
from asus_theye.markets.live import emitir_macro, salvar_registro

NOTA = "KXCPI mede CPI dos EUA; comparável INDIRETO do IPCA (BR) — inflações de países distintos."


def _store(tmp: Path) -> Path:
    store = tmp / "registro.json"
    registro: dict[str, Any] = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-08", agora="2026-08-01T00:00:00Z")
    salvar_registro(store, registro)
    return store


def _observar(tmp: Path, **sobrescreve: Any) -> dict[str, Any]:
    campos: dict[str, Any] = {
        "claim_id": "MACRO-01::2026-08",
        "comparator_price": 0.62,
        "ticker": "KXCPI-26AUG",
        "nota_de_mapeamento": NOTA,
        "store": _store(tmp) if not (tmp / "registro.json").exists() else tmp / "registro.json",
        "arquivo": tmp / "comparador.jsonl",
        "recorded_at": "2026-08-19T12:00:00Z",
    }
    campos.update(sobrescreve)
    return observar_divergencia(**campos)


def test_nota_de_mapeamento_e_ticker_obrigatorios(tmp_path: Path) -> None:
    with pytest.raises(ComparadorError, match="nota_de_mapeamento"):
        _observar(tmp_path, nota_de_mapeamento="  ")
    with pytest.raises(ComparadorError, match="ticker"):
        _observar(tmp_path, ticker="")


def test_claim_fantasma_levanta(tmp_path: Path) -> None:
    with pytest.raises(ComparadorError, match="fantasma"):
        _observar(tmp_path, claim_id="MACRO-01::2099-01")


def test_observacao_mede_e_deduplica_por_conteudo(tmp_path: Path) -> None:
    r1 = _observar(tmp_path)
    assert r1["duplicate"] is False
    assert r1["registro"]["divergence"] == pytest.approx(abs(0.5 - 0.62), abs=1e-6)
    assert "comparador, não fonte" in r1["registro"]["note"]  # a régua viaja no registro
    # mesma observação (mesmo preço) → dedupe, mesmo com recorded_at diferente
    r2 = _observar(tmp_path, recorded_at="2026-08-20T12:00:00Z")
    assert r2["duplicate"] is True
    assert r2["registro"] == r1["registro"]  # o PRIMEIRO registro vence
    # preço NOVO → observação nova
    r3 = _observar(tmp_path, comparator_price=0.55)
    assert r3["duplicate"] is False
    linhas = (tmp_path / "comparador.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 2


def test_observacao_selada_vira_evento_market_comparator(tmp_path: Path) -> None:
    from asus_theye.audit.schema import verify_event
    from asus_theye.markets.auditoria import abrir_auditoria, cabeca_da_corrente

    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=tmp_path / "corrente.jsonl",
        fingerprint=tmp_path / "chave.fingerprint",
    )
    r = _observar(tmp_path, sdk=sdk, eventos=tmp_path / "corrente.jsonl")
    assert r["selagem"] is not None and r["selagem"]["duplicate"] is False
    selado = json.loads((tmp_path / "corrente.jsonl").read_text(encoding="utf-8").strip())
    assert selado["event_type"] == "market.comparator"
    assert verify_event(selado)
    # re-observação idêntica: dedupe no store E na cadeia
    r2 = _observar(tmp_path, sdk=sdk, eventos=tmp_path / "corrente.jsonl", recorded_at="2026-08-21T00:00:00Z")
    assert r2["duplicate"] is True and r2["selagem"]["duplicate"] is True
    assert cabeca_da_corrente(sdk) == 1


def test_preco_fora_de_faixa_levanta(tmp_path: Path) -> None:
    from asus_theye.markets.resolution import ResolutionError

    with pytest.raises(ResolutionError, match="0,1|\\[0,1\\]"):
        _observar(tmp_path, comparator_price=62.0)  # centavos sem converter: pega na porta
