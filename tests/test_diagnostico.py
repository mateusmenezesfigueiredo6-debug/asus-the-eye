# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do doutor local — sem rede e com diagnóstico honesto."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.cli import main
from asus_theye.diagnostico import diagnosticar
from asus_theye.markets.auditoria import abrir_auditoria, selar_registro
from asus_theye.markets.live import emitir_area, salvar_registro


def _home_com_backup(tmp_path: Path, *, criar_backup: bool = True) -> Path:
    home = tmp_path / "home"
    pasta = home / "Área de trabalho" / "organizado" / "Backups" / "the-eye-chaves"
    pasta.mkdir(parents=True, exist_ok=True)
    if criar_backup:
        arquivo = pasta / "the-eye-chaves-2026-08-20.tar.gz.gpg"
        arquivo.write_bytes(b"backup")
    return home


def _estrutura_base(tmp_path: Path, *, eventos: int = 1, criar_backup: bool = True) -> tuple[Path, Path]:
    base = tmp_path / "reports"
    markets = base / "markets"
    audit = base / "audit"
    markets.mkdir(parents=True, exist_ok=True)
    audit.mkdir(parents=True, exist_ok=True)

    chave = bytes.fromhex("11" * 32)
    caminho_chave = audit / "pseudonimos.key"
    caminho_chave.write_text(chave.hex() + "\n", encoding="utf-8")
    eventos_path = markets / "eventos.jsonl"
    sdk = abrir_auditoria(
        audit / "markets-ledger.db",
        chave=chave,
        caminho_chave=caminho_chave,
        eventos=eventos_path,
        fingerprint=markets / "chave.fingerprint",
    )
    for numero in range(1, eventos + 1):
        selar_registro(
            sdk,
            {"n": numero},
            tipo_evento="market.settlement",
            recurso="market",
            correlation_id=f"claim-{numero}",
            eventos=eventos_path,
        )
    (markets / "ancoras.jsonl").write_text(
        json.dumps({"manifest": {"last_sequence": eventos}}) + "\n",
        encoding="utf-8",
    )

    registro = {"versao": 1, "mercados": []}
    emitir_area(registro, "macroeconomia", "2099-12", limiar=0.5, agora="2026-08-20T00:00:00Z")
    salvar_registro(markets / "registro.json", registro)

    (tmp_path / "NOTICE").write_text(
        "ASUS + THE EYE\nCopyright 2026 Mateus Menezes Figueiredo\nLicença: AGPL-3.0-or-later\n",
        encoding="utf-8",
    )
    (tmp_path / "AUTHORS").write_text("Mateus Menezes Figueiredo\n", encoding="utf-8")
    return base, _home_com_backup(tmp_path, criar_backup=criar_backup)


def test_diagnostico_tudo_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base, home = _estrutura_base(tmp_path)
    monkeypatch.setenv("HOME", str(home))

    relatorio = diagnosticar(base)

    assert all(item["ok"] for item in relatorio.values())
    assert relatorio["corrente"]["detalhe"].startswith("1 evento")
    assert "confere" in relatorio["chave"]["detalhe"]


def test_doutor_corrente_quebrada_sai_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    base, home = _estrutura_base(tmp_path, eventos=2)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)

    eventos = base / "markets" / "eventos.jsonl"
    linhas = eventos.read_text(encoding="utf-8").splitlines()
    corrompido = json.loads(linhas[-1])
    corrompido["event_hash_sha256"] = "0" * 64
    linhas[-1] = json.dumps(corrompido)
    eventos.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    code = main(["doutor"])
    saida = capsys.readouterr().out

    assert code == 1
    assert "[CRÍTICO]" in saida
    assert "corrente" in saida
    assert "como corrigir" in saida


def test_diagnostico_chave_com_impressao_divergente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base, home = _estrutura_base(tmp_path)
    monkeypatch.setenv("HOME", str(home))

    chave_hex = (base / "audit" / "pseudonimos.key").read_text(encoding="utf-8").strip()
    (base / "markets" / "chave.fingerprint").write_text("0" * 64 + "\n", encoding="utf-8")

    relatorio = diagnosticar(base)

    assert relatorio["chave"]["ok"] is False
    assert "difere" in relatorio["chave"]["detalhe"]
    assert chave_hex not in relatorio["chave"]["detalhe"]


def test_doutor_backup_ausente_e_aviso_nao_critico(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, home = _estrutura_base(tmp_path, criar_backup=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)

    code = main(["doutor", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["backup"]["ok"] is False
    assert "nenhum backup" in payload["backup"]["detalhe"]
