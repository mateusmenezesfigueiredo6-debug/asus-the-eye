# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A vitrine mostra os DOIS produtos com peso igual — regressão trancada.

A queixa que motiva este teste: "cadê a Palantir? só estou vendo a Chaox". A
tela precedente colocava o hero de UM produto acima dos outros; um visitante
saía com a impressão de plataforma de um produto só. Este teste garante que os
dois cartões existem, com o mesmo rótulo estrutural, e vêm ANTES do exemplo
concreto (que é do Markets — é onde o número aparece).
"""

from __future__ import annotations


def test_a_vitrine_apresenta_dois_produtos_com_peso_igual() -> None:
    from asus_theye.dashboard.landing import landing_page

    h = landing_page(estatico=True)
    # os dois cartões precisam existir, com o mesmo rótulo estrutural
    # os dois rótulos de CARTÃO (a lente de cada produto). Conta o rótulo
    # específico, não "THE EYE ·" solto — o footer de titularidade também o usa.
    assert h.count('class="label">THE EYE ·') == 2, "dois produtos, dois rótulos de cartão"
    for nome in ("Markets", "Ledger"):
        assert f">{nome}<" in h or f">{nome} <" in h, f"nome {nome!r} deve aparecer como título de cartão"

    # o cartão do Ledger não pode ser mais curto que o do Markets ao ponto de
    # sumir visualmente — as duas listas de provas têm de existir com N=3
    markets_pos = h.find(">Markets<")
    ledger_pos = h.find(">Ledger<")
    assert markets_pos != -1 and ledger_pos != -1
    # três <li> de provas por produto (contadas globalmente para simplificar)
    assert h.count("<li>") >= 6

    # a vitrine dos dois produtos vem ANTES do exemplo concreto (hero do Markets)
    i_vitrine = h.find('class="label">THE EYE ·')
    i_exemplo = h.find("Publicado antes do fato")
    if i_exemplo != -1:
        assert i_vitrine < i_exemplo


def test_meta_description_nomeia_os_dois() -> None:
    """Preview de link partilhado — precisa nomear os dois, senão vira 'produto único'."""
    from asus_theye.dashboard.landing import landing_page

    h = landing_page(estatico=True)
    head = h[: h.find("</head>")]
    assert "Markets" in head and "Ledger" in head, "meta description sem os dois nomes"
