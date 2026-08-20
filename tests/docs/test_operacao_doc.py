# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verificações mínimas do guia de operação."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DOC = RAIZ / "docs" / "OPERACAO.md"


def _subcomandos() -> list[str]:
    ajuda = subprocess.run(
        [sys.executable, "-m", "asus_theye.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        check=False,
    )
    assert ajuda.returncode == 0, ajuda.stderr or ajuda.stdout or "falha ao ler --help do CLI"
    nomes = [
        match.group(1)
        for match in re.finditer(r"^\s{2,6}([a-z0-9-]+)\s{2,}", ajuda.stdout, flags=re.MULTILINE)
        if not match.group(1).startswith("-")
    ]
    assert nomes, "nenhum subcomando encontrado no --help do CLI"
    return nomes


def test_operacao_lista_todos_os_subcomandos_reais() -> None:
    texto = DOC.read_text(encoding="utf-8")
    for nome in _subcomandos():
        assert f"`{nome}`" in texto, f"docs/OPERACAO.md não lista {nome}"


def test_operacao_tem_rodape_e_custodia() -> None:
    texto = DOC.read_text(encoding="utf-8")
    assert "© 2026 Mateus Menezes Figueiredo, AGPL-3.0." in texto
    assert "./scripts/backup_chaves.sh" in texto
    assert "./scripts/backup_chaves.sh --verificar" in texto
