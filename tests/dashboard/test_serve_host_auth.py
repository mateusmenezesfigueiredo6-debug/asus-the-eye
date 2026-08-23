# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A auth do dashboard deriva do HOST efetivo, não da flag --expose.

O defeito que isto trava: ``--host 0.0.0.0`` sem ``--expose`` subia na rede SEM
token, porque ``require_auth`` vinha de ``args.expose``. A garantia fail-closed
cobria só um dos dois caminhos de exposição. Rede é rede — exige token, venha
de onde vier.
"""

from __future__ import annotations

import pytest

from asus_theye.cli import _e_loopback


@pytest.mark.parametrize(
    ("host", "esperado_loopback"),
    [
        ("127.0.0.1", True),
        ("127.0.0.5", True),  # todo o /8 é loopback
        ("::1", True),
        ("localhost", True),
        ("0.0.0.0", False),  # o caso do defeito: parece "sem host", é a rede inteira
        ("192.168.0.10", False),
        ("10.0.0.1", False),
        ("meu-servidor.lan", False),  # nome não-localhost: trate como rede
        ("", False),  # host vazio é ambíguo -> fail-closed, exige token
    ],
)
def test_classificacao_de_host(host: str, esperado_loopback: bool) -> None:
    assert _e_loopback(host) is esperado_loopback


def test_o_defeito_em_uma_linha() -> None:
    """0.0.0.0 é a rede inteira e PRECISA de auth; loopback não."""
    assert _e_loopback("0.0.0.0") is False  # => require_auth=True => recusa sem token
    assert _e_loopback("127.0.0.1") is True  # => local, sobe sem token
