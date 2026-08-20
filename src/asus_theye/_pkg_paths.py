# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Caminhos de dados empacotados — independente do layout do repositório.

Motivo: ``Path(__file__).parents[N]`` só acerta no layout de repositório.
Instalado como pacote regular (``pip install .``), ``__file__`` resolve para
dentro de ``site-packages`` onde os dados não estão.

Use sempre ``pkg_data("subdir", "arquivo.json")`` em vez de manipulação
de ``__file__``.  O retorno é um ``Path`` real apontando para o arquivo
dentro do pacote instalado.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

_PKG = importlib.resources.files("asus_theye")


def pkg_data(*parts: str) -> Path:
    """Retorna o caminho absoluto de um arquivo de dados dentro do pacote.

    Exemplos::

        pkg_data("data", "legal-taxonomy", "legal_areas.master.json")
        pkg_data("migrations", "0001_audit_ledger.sql")

    Funciona tanto no layout de repositório quanto instalado via ``pip``.
    """
    ref = _PKG
    for part in parts:
        ref = ref.joinpath(part)
    return Path(ref)  # type: ignore[arg-type]
