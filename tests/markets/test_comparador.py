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

NOTA = "COMPARADOR-DEMO mede CPI dos EUA; comparável INDIRETO do IPCA (BR) — inflações de países distintos."


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
        "ticker": "COMPARADOR-DEMO-26AUG",
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


# --------------------------------------------------- consenso Focus em rotina


class _TransporteFocus:
    """Olinda devolve mediana; SGS devolve série vazia do mês (sem prévia)."""

    def __init__(self, olinda_body: bytes) -> None:
        self._olinda = olinda_body

    def request(self, url, *, headers, timeout, max_bytes):
        from asus_theye.net.http import HttpResponse

        if "olinda.bcb.gov.br" in url:
            return HttpResponse(url=url, status=200, headers={}, body=self._olinda)
        return HttpResponse(url=url, status=200, headers={}, body=b'[{"data":"01/07/2026","valor":"0.30"}]')


_OLINDA_MEDIANA = (
    b'{"value":[{"Indicador":"IPCA","Data":"2026-08-21","DataReferencia":"08/2026","Mediana":0.10}]}'
)
_OLINDA_VAZIO = b'{"value":[]}'


def _mercado_aberto(tmp_path):
    registro = {
        "versao": 1,
        "mercados": [
            {
                "claim_id": "MACRO-01::2026-08",
                "market_area_id": "macroeconomia",
                "question": "IPCA?",
                "probability": 0.2,
                "deadline": "2026-08-31",
                "resolution_source": "api.bcb.gov.br (SGS)",
                "created_at": "2026-08-17T15:17:37.489807Z",
                "mes_referencia": "2026-08",
                "limiar": 0.5,
                "estado": "ABERTO",
            }
        ],
    }
    store = tmp_path / "registro.json"
    store.write_text(json.dumps(registro), encoding="utf-8")
    return store, registro["mercados"][0]


def test_consenso_focus_observa_e_deduplica(tmp_path):
    from asus_theye.markets.comparador import observar_consenso_focus

    store, mercado = _mercado_aberto(tmp_path)
    transporte = _TransporteFocus(_OLINDA_MEDIANA)
    primeira = observar_consenso_focus(
        mercado, dia="2026-08-28", store=store, transport=transporte
    )
    assert primeira["acao"] == "consenso_observado"
    linhas = (tmp_path / "comparador.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 1
    registro = json.loads(linhas[0])
    assert registro["comparator"] == "Focus/BCB"
    assert "Kalshi" not in registro["comparator"]

    segunda = observar_consenso_focus(
        mercado, dia="2026-08-29", store=store, transport=transporte
    )
    assert segunda["acao"] == "consenso_duplicado"
    assert len((tmp_path / "comparador.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_consenso_focus_sem_mediana_e_unknown(tmp_path):
    from asus_theye.markets.comparador import observar_consenso_focus

    store, mercado = _mercado_aberto(tmp_path)
    acao = observar_consenso_focus(
        mercado, dia="2026-08-28", store=store, transport=_TransporteFocus(_OLINDA_VAZIO)
    )
    assert acao["acao"] == "consenso_indisponivel"
    assert not (tmp_path / "comparador.jsonl").exists()
