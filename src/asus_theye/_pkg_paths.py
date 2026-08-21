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


# Origens possíveis de um dado que muda depois do build. Viajam DENTRO do hash.
ORIGEM_VIVO = "cwd"
ORIGEM_EMPACOTADO = "package"


def dado_vivo_ou_empacotado(*parts: str) -> tuple[Path, str]:
    """Resolve um dado que a operação REESCREVE, e diz de onde ele veio.

    Nem todo dado é igual. ``legal_areas.master.json`` é constante: a cópia do
    pacote é a verdade. Já ``data/source-graph/sources.json`` é **reescrito**
    pela descoberta, então a cópia do pacote é uma foto do dia do build e o
    arquivo do diretório de trabalho é o estado atual.

    Ler o mesmo nome de dois lugares diferentes, em dois comandos diferentes, é
    o defeito que esta função existe para acabar: ``asus-theye source-graph`` e
    ``asus-theye chart`` chegavam a imprimir coberturas DIFERENTES, e as duas
    eram hasheáveis e seláveis, sem registrar de qual árvore veio o insumo.

    Devolve ``(caminho, origem)``. A origem não é decoração: quem sela precisa
    gravá-la, porque dois snapshots de safras diferentes com o mesmo hash é
    exatamente o tipo de coisa que uma corrente auditável não pode permitir.

    O vivo tem precedência sobre o empacotado — quem rodou a descoberta espera
    ver o resultado dela, não a foto do build.
    """
    vivo = Path(*parts)
    if vivo.exists():
        return vivo, ORIGEM_VIVO
    return pkg_data(*parts), ORIGEM_EMPACOTADO
