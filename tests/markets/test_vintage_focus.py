# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do vintage do Focus — offline, transporte falso."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.markets.vintage_focus import VintageError, arquivar_vintage, serie_vintage
from asus_theye.net.http import HttpResponse

COM_BOLETIM = b'{"value":[{"Data":"2026-08-14","Mediana":0.52}]}'
OUTRO_BOLETIM = b'{"value":[{"Data":"2026-08-21","Mediana":0.55}]}'
SEM_BOLETIM = b'{"value":[]}'


class TransporteFalso:
    def __init__(self, corpo: bytes = COM_BOLETIM, status: int = 200) -> None:
        self.corpo, self.status = corpo, status

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.corpo)


def test_arquiva_e_deduplica_o_mesmo_boletim(tmp_path: Path) -> None:
    r1 = arquivar_vintage("2026-09", base=tmp_path, transport=TransporteFalso(), agora="2026-08-20T00:00:00Z")
    assert r1["duplicate"] is False
    assert r1["registro"]["mediana"] == pytest.approx(0.52)
    assert "vintage, não revisado" in r1["registro"]["metodo"]

    # mesmo boletim, captura mais tarde → dedupe (não polui a série)
    r2 = arquivar_vintage("2026-09", base=tmp_path, transport=TransporteFalso(), agora="2026-08-21T00:00:00Z")
    assert r2["duplicate"] is True
    assert len(serie_vintage("2026-09", base=tmp_path)) == 1

    # boletim NOVO → vintage novo (é exatamente o que forma a série)
    r3 = arquivar_vintage(
        "2026-09", base=tmp_path, transport=TransporteFalso(OUTRO_BOLETIM), agora="2026-08-22T00:00:00Z"
    )
    assert r3["duplicate"] is False
    assert len(serie_vintage("2026-09", base=tmp_path)) == 2


def test_mes_sem_boletim_e_honesto(tmp_path: Path) -> None:
    r = arquivar_vintage("2027-01", base=tmp_path, transport=TransporteFalso(SEM_BOLETIM))
    assert r["registro"] is None and "não publicado" in r["motivo"]
    assert serie_vintage(base=tmp_path) == []  # ausência não vira zero


def test_fonte_quebrada_levanta(tmp_path: Path) -> None:
    with pytest.raises(VintageError, match="indisponível"):
        arquivar_vintage("2026-09", base=tmp_path, transport=TransporteFalso(b"nao-e-json"))


def test_snapshot_bruto_fica_ao_lado(tmp_path: Path) -> None:
    arquivar_vintage("2026-09", base=tmp_path, transport=TransporteFalso(), agora="2026-08-20T00:00:00Z")
    brutos = list((tmp_path / "vintage").glob("focus-2026-09-*.json"))
    assert len(brutos) == 1
    dados = json.loads(brutos[0].read_text(encoding="utf-8"))
    assert dados["data_do_boletim"] == "2026-08-14" and dados["fonte"].startswith("api.bcb.gov.br")


def test_vintage_selado_vira_evento_verificavel(tmp_path: Path) -> None:
    from asus_theye.audit.schema import verify_event
    from asus_theye.markets.auditoria import abrir_auditoria

    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=tmp_path / "corrente.jsonl",
        fingerprint=tmp_path / "chave.fingerprint",
    )
    r = arquivar_vintage(
        "2026-09",
        base=tmp_path,
        transport=TransporteFalso(),
        sdk=sdk,
        eventos=tmp_path / "corrente.jsonl",
        agora="2026-08-20T00:00:00Z",
    )
    assert r["selagem"] is not None and r["selagem"]["duplicate"] is False
    selado = json.loads((tmp_path / "corrente.jsonl").read_text(encoding="utf-8").strip())
    assert selado["event_type"] == "market.vintage" and verify_event(selado)
