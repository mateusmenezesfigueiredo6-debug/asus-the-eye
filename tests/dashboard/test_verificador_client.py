# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""O verificador client-side gera uma página funcional e autocontida.

Não dá para rodar o JS aqui sem um navegador; o que este teste garante é o que
importa para o lançamento: a página existe, é autocontida (sem rede), tem a
lógica de verificação embutida, e o export a inclui. A prova de que o JS de
fato verifica é feita à mão no navegador (passo 5 do lançamento).
"""

from __future__ import annotations

import re

from pathlib import Path

# O CPF do titular NÃO é escrito aqui. Estes testes existem para provar que ele
# nunca sai no export público — mas a versão anterior citava o número literal,
# e o arquivo é versionado num repositório com remoto. O teste que protegia o
# dado era o que o expunha. Agora casamos o FORMATO, não o valor: pega qualquer
# CPF, inclusive um que ainda não existe no código.
CPF_FORMATADO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
# 11 dígitos crus, mas NÃO dentro de um hash: um sha256 tem 11 dígitos
# decimais seguidos com facilidade, e isso não é CPF nenhum.
CPF_CRU = re.compile(r"(?<![0-9a-fA-F])\d{11}(?![0-9a-fA-F])")



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
    assert not CPF_FORMATADO.search(h), "CPF formatado na página pública"
    assert not CPF_CRU.search(h), "sequência de 11 dígitos (CPF?) na página pública"
    assert "@gmail.com" not in h
