# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Trava mínima de responsividade dos painéis do dashboard."""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("relpath", "marcadores", "tem_wrapper"),
    [
        ("src/asus_theye/dashboard/projeto.py", ("MEDIÇÃO DO PROJETO", "Roteiro dos produtos", "Caminho mínimo"), True),
        ("src/asus_theye/dashboard/corrente.py", ("CORRENTE", "Legendas por tipo", "conteúdo não sai daqui"), True),
        ("src/asus_theye/dashboard/mercados.py", ("MERCADOS", "Mercados vivos", "Divergência vs comparador"), True),
        ("src/asus_theye/dashboard/evidencia.py", ("EVIDÊNCIA", "Linhagem verificável", "Fonte provada"), False),
        ("src/asus_theye/dashboard/mlops.py", ("MLOPS", "Corridas", "Campeão / Desafiante por modelo"), True),
        ("src/asus_theye/dashboard/benchmark.py", ("ASUS THE EYE BENCHMARK", "Best score", "Score comparison"), False),
    ],
)
def test_paineis_tem_trava_responsiva_sem_perder_marcadores(
    relpath: str, marcadores: tuple[str, ...], tem_wrapper: bool
) -> None:
    texto = (RAIZ / relpath).read_text(encoding="utf-8")
    assert "@media (max-width: 640px)" in texto
    assert "overflow-x:auto" in texto
    assert ('class="table-wrap"' in texto) is tem_wrapper
    for marcador in marcadores:
        assert marcador in texto
