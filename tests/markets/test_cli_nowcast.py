# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do subcomando ``asus-theye markets-nowcast`` — nenhuma chamada de rede."""

from __future__ import annotations

import json

import pytest

from asus_theye.cli import main


def _corrida_fake(especificacao: str, **_kw):  # type: ignore[no-untyped-def]
    from asus_theye.mlops.rastreio import Corrida

    return Corrida(
        modelo_id="ipca-nowcast-linear",
        versao="0.0.0",
        executada_em="2026-01-01T00:00:00Z",
        params={"brier_ridge": 0.12, "n_meses": 3, "especificacao": especificacao, "janela": 120},
        metricas={},
        artefatos=[{"caminho": "/tmp/manifesto.json", "sha256": "abc123"}],
    )


def test_nowcast_cli_saida_texto(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from asus_theye.markets import nowcast as _nowcast

    monkeypatch.setattr(_nowcast, "corrida_do_nowcast", _corrida_fake)
    code = main(["markets-nowcast", "--spec", "R2"])
    out = capsys.readouterr().out
    assert code == 0
    assert "NOWCAST IPCA" in out
    assert "R2" in out
    assert "0.12" in out


def test_nowcast_cli_saida_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from asus_theye.markets import nowcast as _nowcast

    monkeypatch.setattr(_nowcast, "corrida_do_nowcast", _corrida_fake)
    code = main(["markets-nowcast", "--spec", "R4", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["especificacao"] == "R4"
    assert "manifesto" in payload
    assert "sha256" in payload


def test_nowcast_cli_erro_de_rede(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from asus_theye.markets import nowcast as _nowcast

    def _falha(especificacao: str, **_kw) -> None:  # type: ignore[return]
        raise _nowcast.NowcastError("SGS indisponível (teste)")

    monkeypatch.setattr(_nowcast, "corrida_do_nowcast", _falha)
    code = main(["markets-nowcast"])
    out = capsys.readouterr().out
    assert code == 1
    assert "SGS indisponível" in out
