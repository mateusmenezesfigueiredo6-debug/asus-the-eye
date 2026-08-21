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
def test_a_trava_responsiva_vive_no_tema_e_nao_copiada(  # noqa: ARG001
    relpath: str, marcadores: tuple[str, ...], tem_wrapper: bool
) -> None:
    """As regras responsivas moraram em dez cópias e agora moram numa só.

    Dez cópias divergem: uma ganha um ajuste, outra não, e o produto passa a
    parecer dez produtos. O teste antigo exigia a regra DENTRO de cada painel, o
    que travava justamente a correção. Agora ele exige que a regra exista no
    tema — e que cada painel continue dizendo o que precisa dizer.
    """
    tema = (RAIZ / "src/asus_theye/dashboard/tema.py").read_text(encoding="utf-8")
    assert "@media (max-width: 640px)" in tema
    assert "overflow-x:auto" in tema
    assert ".table-wrap" in tema, "a classe antiga tem de continuar válida — os painéis ainda a emitem"

    texto = (RAIZ / relpath).read_text(encoding="utf-8")
    assert ('class="table-wrap"' in texto) is tem_wrapper
    for marcador in marcadores:
        assert marcador in texto
