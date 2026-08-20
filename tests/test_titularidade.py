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


def test_todo_terceiro_do_notice_tem_proveniencia() -> None:
    """O NOTICE promete registro em reports/provenance/ para cada absorção.

    Promessa sem arquivo é promessa quebrada — e a que mais importa é a única
    CÓPIA literal (OpenZeppelin), não as reimplementações.
    """
    notice = (RAIZ / "NOTICE").read_text(encoding="utf-8")
    registros = " ".join(p.read_text(encoding="utf-8") for p in (RAIZ / "reports/provenance").glob("*.md"))
    for terceiro in ("SocialPredict", "Dask", "MLflow", "OpenZeppelin"):
        assert terceiro in notice, f"{terceiro} sumiu do NOTICE"
        assert terceiro in registros, f"{terceiro} está no NOTICE mas não tem proveniência registrada"


def test_obra_de_terceiro_nao_leva_o_nome_do_titular() -> None:
    """Carimbar código alheio seria o oposto do que a política existe para fazer."""
    lib = RAIZ / "contracts/audit-anchor/lib/openzeppelin-contracts"
    if not lib.exists():
        return
    carimbados = [p for p in lib.rglob("*.sol") if "Mateus Menezes Figueiredo" in p.read_text(encoding="utf-8")]
    assert not carimbados, f"obra de terceiro carimbada indevidamente: {carimbados[:3]}"
