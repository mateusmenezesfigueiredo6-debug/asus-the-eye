# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verificações mínimas do guia de operação."""

from __future__ import annotations

from pathlib import Path

from asus_theye.cli import _parser

RAIZ = Path(__file__).resolve().parents[2]
DOC = RAIZ / "docs" / "OPERACAO.md"


def _subcomandos() -> list[str]:
    parser = _parser()
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if choices:
            return list(choices)
    raise AssertionError("parser sem choices de subcomando")


def test_operacao_lista_todos_os_subcomandos_reais() -> None:
    texto = DOC.read_text(encoding="utf-8")
    for nome in _subcomandos():
        assert f"`{nome}`" in texto, f"docs/OPERACAO.md não lista {nome}"


def test_operacao_tem_rodape_e_custodia() -> None:
    texto = DOC.read_text(encoding="utf-8")
    assert "© 2026 Mateus Menezes Figueiredo, AGPL-3.0." in texto
    assert "./scripts/backup_chaves.sh" in texto
    assert "./scripts/backup_chaves.sh --verificar" in texto
