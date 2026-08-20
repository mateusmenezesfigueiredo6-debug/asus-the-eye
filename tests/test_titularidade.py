# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Política: TODO arquivo-fonte declara a titularidade do dono.

Um NOTICE na raiz declara a obra; o cabeçalho SPDX declara CADA arquivo —
que é o que viaja quando alguém copia um módulo solto. Este teste é a trava:
arquivo novo sem o carimbo reprova no CI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_todo_arquivo_declara_a_titularidade() -> None:
    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts/aplicar_titularidade.py"), "--conferir"],
        capture_output=True,
        text=True,
        cwd=RAIZ,
    )
    assert r.returncode == 0, f"arquivo(s) sem titularidade:\n{r.stdout}{r.stderr}"


def test_notice_e_authors_nomeiam_o_titular() -> None:
    for arquivo in ("NOTICE", "AUTHORS"):
        texto = (RAIZ / arquivo).read_text(encoding="utf-8")
        assert "Mateus Menezes Figueiredo" in texto, f"{arquivo} não nomeia o titular"
    assert "AGPL-3.0" in (RAIZ / "NOTICE").read_text(encoding="utf-8")
