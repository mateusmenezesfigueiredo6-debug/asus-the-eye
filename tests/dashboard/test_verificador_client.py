# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""O verificador client-side gera uma página funcional e autocontida.

Não dá para rodar o JS aqui sem um navegador; o que este teste garante é o que
importa para o lançamento: a página existe, é autocontida (sem rede), tem a
lógica de verificação embutida, e o export a inclui. A prova de que o JS de
fato verifica é feita à mão no navegador (passo 5 do lançamento).
"""

from __future__ import annotations

from pathlib import Path


def test_pagina_do_verificador_e_autocontida() -> None:
    from asus_theye.dashboard.verificador import verificador_page

    h = verificador_page(estatico=True)
    # a lógica portada do worker.ts tem de estar embutida
    for marca in ("crypto.subtle", "jsonCanonico", "verificarEvento", "verificarCadeia", "GENESIS"):
        assert marca in h, f"lógica ausente: {marca}"
    # autocontido: nenhuma chamada de rede de verdade. (O namespace do SVG do
    # favicon, http://www.w3.org/2000/svg, é identificador XML — não é fetch.)
    for proibido in ("fetch(", "XMLHttpRequest", "https://fonts", "<script src", "<img "):
        assert proibido not in h, f"a página não pode telefonar para fora: {proibido}"
    # tem o aviso de escopo (herdado do tema)
    assert "não é casa de apostas" in h


def test_export_inclui_verificar_html(tmp_path: Path) -> None:
    from asus_theye.dashboard.export_static import exportar

    resultado = exportar(tmp_path)
    assert "verificar.html" in resultado["gerados"]
    conteudo = (tmp_path / "verificar.html").read_text(encoding="utf-8")
    assert "crypto.subtle" in conteudo
    assert "<!doctype html>" in conteudo.lower()


def test_verificar_nao_expoe_dado_pessoal(tmp_path: Path) -> None:
    """Trava de titularidade: a página pública não pode vazar CPF nem e-mail."""
    from asus_theye.dashboard.verificador import verificador_page

    h = verificador_page(estatico=True)
    assert "158.035.377" not in h and "15803537705" not in h
    assert "@gmail.com" not in h
