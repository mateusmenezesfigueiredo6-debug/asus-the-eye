"""Testes do subcomando ``asus-theye mlops-promover``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye import cli
from asus_theye.mlops import Modelo, Versao, registrar_modelo, registrar_versao


def test_cli_mlops_promover_sem_versao_registrada_sai_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    code = cli.main(
        [
            "mlops-promover",
            "--modelo",
            "m1",
            "--versao",
            "1.0.0",
            "--papel",
            "campeao",
            "--motivo",
            "baseline inicial",
            "--no-audit",
        ]
    )
    out = capsys.readouterr().out
    assert "mlops-promover:" in out
    assert code == 1


def test_cli_mlops_promover_no_audit_fluxo_feliz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    registrar_modelo(
        Modelo(modelo_id="m1", nome="Modelo Um", area="macro", objetivo="prever"),
        base=tmp_path / "reports" / "mlops",
    )
    registrar_versao(
        Versao(modelo_id="m1", versao="1.0.0", origem="tests"),
        base=tmp_path / "reports" / "mlops",
    )
    code = cli.main(
        [
            "mlops-promover",
            "--modelo",
            "m1",
            "--versao",
            "1.0.0",
            "--papel",
            "desafiante",
            "--motivo",
            "teste A/B",
            "--no-audit",
        ]
    )
    assert code == 0
    promocoes = (tmp_path / "reports" / "mlops" / "promocoes.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(promocoes) == 1


def test_cli_mlops_promover_json_traz_registro_papel_campeao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    registrar_modelo(
        Modelo(modelo_id="m1", nome="Modelo Um", area="macro", objetivo="prever"),
        base=tmp_path / "reports" / "mlops",
    )
    registrar_versao(
        Versao(modelo_id="m1", versao="1.0.0", origem="tests"),
        base=tmp_path / "reports" / "mlops",
    )
    code = cli.main(
        [
            "mlops-promover",
            "--modelo",
            "m1",
            "--versao",
            "1.0.0",
            "--papel",
            "campeao",
            "--motivo",
            "baseline inicial",
            "--json",
            "--no-audit",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["registro"]["papel"] == "campeao"
    assert code == 0
