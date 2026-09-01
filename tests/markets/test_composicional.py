# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Matemática composicional compartilhada — o módulo que fecha a duplicação.

Foco no que motivou a extração: o parâmetro ``erro`` injetável precisa
funcionar mesmo quando ninguém o passa (usa o genérico), e a proteção contra
overflow de ``de_clr`` precisa valer para qualquer chamador, não só para quem
lembrou de reimplementá-la.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.composicional import ComposicionalError, clr, de_clr, normalizar


class ErroDoChamador(RuntimeError):
    pass


def test_ida_e_volta_fecha():
    c = {"A": 0.5, "B": 0.3, "C": 0.2}
    assert de_clr(clr(c)) == pytest.approx(c)


def test_erro_padrao_e_composicional_error():
    with pytest.raises(ComposicionalError):
        clr({"A": 1, "B": -1})


def test_erro_injetado_e_o_que_sai_nao_o_generico():
    with pytest.raises(ErroDoChamador):
        clr({"A": 1, "B": -1}, erro=ErroDoChamador)
    with pytest.raises(ErroDoChamador):
        de_clr({}, erro=ErroDoChamador)
    with pytest.raises(ErroDoChamador):
        normalizar({"A": 0.0}, erro=ErroDoChamador)


def test_de_clr_nao_estoura_com_coordenada_grande():
    """A proteção central: subtrair o máximo antes de exponenciar."""
    resultado = de_clr({"A": 750.0, "B": -375.0, "C": -375.0})
    assert sum(resultado.values()) == pytest.approx(1.0)


def test_composicao_vazia_e_recusada():
    with pytest.raises(ComposicionalError, match="vazia"):
        clr({})


def test_fatia_zerada_nao_impede_o_calculo():
    """Zero é ausência de sinal, não impossibilidade."""
    fatias = de_clr(clr({"A": 0.9, "B": 0.1, "C": 0.0}))
    assert fatias["C"] > 0.0
    assert fatias["C"] < 1e-3
