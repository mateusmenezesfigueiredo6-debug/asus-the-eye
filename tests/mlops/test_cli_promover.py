# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da CLI mlops-promover.

Molde: test_cli_mlops_benchmark_* em tests/mlops/test_rastreio.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _preparar(base: Path) -> None:
    """Registra modelo e versão para que a promoção tenha referência."""
    from asus_theye.mlops import Modelo, Versao, registrar_modelo, registrar_versao

    registrar_modelo(
        Modelo(modelo_id="m1", nome="Modelo Teste", area="previsao", objetivo="testar CLI"),
        base=base,
        sdk=None,
    )
    registrar_versao(
        Versao(modelo_id="m1", versao="v1", origem="tests"),
        base=base,
        sdk=None,
    )


# ------------------------------------------------------------------ testes


def test_cli_promover_sem_versao_registrada_sai_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Versão inexistente → mensagem + exit 1."""
    from asus_theye import cli

    monkeypatch.chdir(tmp_path)
    assert (
        cli.main(
            [
                "mlops-promover",
                "--modelo",
                "m1",
                "--versao",
                "v99",
                "--papel",
                "campeao",
                "--motivo",
                "teste",
                "--no-audit",
            ]
        )
        == 1
    )


def test_cli_promover_fluxo_feliz_no_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fluxo feliz --no-audit: registra modelo+versão, promove, exit 0, promocoes.jsonl ganha 1 linha."""
    from asus_theye import cli

    monkeypatch.chdir(tmp_path)
    base = tmp_path / "reports" / "mlops"
    _preparar(base)

    assert (
        cli.main(
            [
                "mlops-promover",
                "--modelo",
                "m1",
                "--versao",
                "v1",
                "--papel",
                "campeao",
                "--motivo",
                "primeiro campeão do teste",
                "--no-audit",
            ]
        )
        == 0
    )
    linhas = (base / "promocoes.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 1
    registro = json.loads(linhas[0])
    assert registro["papel"] == "campeao"
    assert registro["modelo_id"] == "m1"


def test_cli_promover_json_retorna_papel_campeao(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--json devolve JSON com registro.papel == 'campeao'."""
    from asus_theye import cli

    monkeypatch.chdir(tmp_path)
    base = tmp_path / "reports" / "mlops"
    _preparar(base)

    saida: list[str] = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: saida.append(str(a[0]) if a else ""))

    code = cli.main(
        [
            "mlops-promover",
            "--modelo",
            "m1",
            "--versao",
            "v1",
            "--papel",
            "campeao",
            "--motivo",
            "melhor Brier",
            "--no-audit",
            "--json",
        ]
    )
    assert code == 0
    dados = json.loads("\n".join(saida))
    assert dados["resultado"]["registro"]["papel"] == "campeao"
