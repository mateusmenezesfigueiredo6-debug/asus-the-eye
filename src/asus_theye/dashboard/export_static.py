# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Exportação estática dos painéis do dashboard para dist/.

Chama as funções de página existentes (puras) e escreve arquivos HTML em
*destino*.  Nunca inventa conteúdo: se um painel depender de recurso ausente,
o arquivo é pulado e o motivo é registrado no retorno.
"""

from __future__ import annotations

import os
from pathlib import Path

from asus_theye.dashboard.api_docs import api_docs_page
from asus_theye.dashboard.benchmark import benchmark_page
from asus_theye.dashboard.calibracao import calibracao_page
from asus_theye.dashboard.corrente import corrente_page
from asus_theye.dashboard.evidencia import evidencia_page
from asus_theye.dashboard.landing import landing_page
from asus_theye.dashboard.mercados import mercados_page
from asus_theye.dashboard.mlops import mlops_page
from asus_theye.dashboard.projeto import projeto_page
from asus_theye.dashboard.verificador import verificador_page

# Painéis de telemetria INTERNA — a "fábrica", não os produtos. Ficam fora do
# menu público (navegacao.PAINEIS_INTERNOS) e, no bundle PÚBLICO, fora do dist:
# a vitrine mostra os produtos, não a instrumentação da obra (decisão do PR #94).
# São eles também que carregam menções factuais à Chaox (o expurgo, o M4) —
# corretas no registro interno, fora de lugar no site público.
PAINEIS_INTERNOS_HTML = ("projeto.html", "mlops.html", "benchmark.html")


def exportar(destino: Path, *, publico: bool = False) -> dict[str, list[str]]:
    """Renderiza os painéis do dashboard como HTML estático em *destino*.

    Retorna ``{"gerados": [...], "pulados": [...]}``.  Nunca escreve arquivo
    vazio fingindo dado; painel dependente de recurso ausente é pulado com
    explicação honesta.

    ``publico=True`` gera o bundle de LANÇAMENTO: exclui a telemetria interna
    (``PAINEIS_INTERNOS_HTML``), para que o site público seja só os dois
    produtos. O default ``False`` gera tudo — é o que a suíte e o dev usam.
    """
    destino.mkdir(parents=True, exist_ok=True)

    gerados: list[str] = []
    pulados: list[str] = []

    def escrever(nome: str, html: str) -> None:
        if publico and nome in PAINEIS_INTERNOS_HTML:
            pulados.append(f"{nome}: telemetria interna, fora do bundle público")
            return
        (destino / nome).write_text(html, encoding="utf-8")
        gerados.append(nome)

    # --- projeto.html --------------------------------------------------------
    escrever("projeto.html", projeto_page(estatico=True))

    # --- evidencia.html ------------------------------------------------------
    escrever("evidencia.html", evidencia_page(estatico=True))

    # --- calibracao.html -----------------------------------------------------
    escrever("calibracao.html", calibracao_page(estatico=True))

    # --- corrente.html -------------------------------------------------------
    escrever("corrente.html", corrente_page(estatico=True))

    # --- mercados.html -------------------------------------------------------
    escrever("mercados.html", mercados_page(estatico=True))

    # --- verificar.html ------------------------------------------------------
    # A única página com JS, por necessidade declarada: a verificação roda no
    # navegador de quem verifica. Ver docstring de dashboard/verificador.py.
    escrever("verificar.html", verificador_page(estatico=True))

    # --- benchmark.html ------------------------------------------------------
    escrever("benchmark.html", benchmark_page(estatico=True))

    # --- mlops.html ----------------------------------------------------------
    escrever("mlops.html", mlops_page(estatico=True))

    # --- api.html ------------------------------------------------------------
    escrever("api.html", api_docs_page(estatico=True))

    # --- markets.html --------------------------------------------------------
    db_env = os.environ.get("ASUS_MARKETS_DB", "")
    if db_env and Path(db_env).exists():
        from asus_theye.dashboard.markets import markets_page

        (destino / "markets.html").write_text(markets_page(db_env, estatico=True), encoding="utf-8")
        gerados.append("markets.html")
    else:
        if not db_env:
            motivo = "markets: ASUS_MARKETS_DB ausente"
        else:
            motivo = f"markets: arquivo não encontrado ({db_env})"
        pulados.append(motivo)

    # --- index.html ----------------------------------------------------------
    # O index É a landing. Antes daqui vivia um template próprio com uma lista
    # crua de links — escrito antes de landing.py existir. Quem abrisse o site
    # publicado via um índice técnico, não o produto. Uma página só, dois meios.
    (destino / "index.html").write_text(landing_page(estatico=True), encoding="utf-8")
    gerados.append("index.html")

    return {"gerados": gerados, "pulados": pulados}
