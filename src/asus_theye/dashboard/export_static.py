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
from asus_theye.dashboard.mercados import mercados_page
from asus_theye.dashboard.mlops import mlops_page
from asus_theye.dashboard.projeto import projeto_page

_INDEX_TEMPLATE = """\
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>THE EYE — painéis</title>
<style>
  body {{ background:#111; color:#e0e0e0; font-family:monospace; padding:2rem; }}
  h1 {{ color:#4fc3f7; margin-bottom:1.5rem; }}
  ul {{ list-style:none; padding:0; }}
  li {{ margin:.5rem 0; }}
  a {{ color:#80cbc4; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
</style>
</head>
<body>
<main>
<h1>THE EYE — painéis</h1>
<ul>
{items}
</ul>
</main>
</body>
</html>
"""


def exportar(destino: Path) -> dict[str, list[str]]:
    """Renderiza os painéis do dashboard como HTML estático em *destino*.

    Retorna ``{"gerados": [...], "pulados": [...]}``.  Nunca escreve arquivo
    vazio fingindo dado; painel dependente de recurso ausente é pulado com
    explicação honesta.
    """
    destino.mkdir(parents=True, exist_ok=True)

    gerados: list[str] = []
    pulados: list[str] = []

    # --- projeto.html --------------------------------------------------------
    (destino / "projeto.html").write_text(projeto_page(), encoding="utf-8")
    gerados.append("projeto.html")

    # --- evidencia.html ------------------------------------------------------
    (destino / "evidencia.html").write_text(evidencia_page(), encoding="utf-8")
    gerados.append("evidencia.html")

    # --- calibracao.html -----------------------------------------------------
    (destino / "calibracao.html").write_text(calibracao_page(), encoding="utf-8")
    gerados.append("calibracao.html")

    # --- corrente.html -------------------------------------------------------
    (destino / "corrente.html").write_text(corrente_page(), encoding="utf-8")
    gerados.append("corrente.html")

    # --- mercados.html -------------------------------------------------------
    (destino / "mercados.html").write_text(mercados_page(), encoding="utf-8")
    gerados.append("mercados.html")

    # --- benchmark.html ------------------------------------------------------
    (destino / "benchmark.html").write_text(benchmark_page(), encoding="utf-8")
    gerados.append("benchmark.html")

    # --- mlops.html ----------------------------------------------------------
    (destino / "mlops.html").write_text(mlops_page(), encoding="utf-8")
    gerados.append("mlops.html")

    # --- api.html ------------------------------------------------------------
    (destino / "api.html").write_text(api_docs_page(), encoding="utf-8")
    gerados.append("api.html")

    # --- markets.html --------------------------------------------------------
    db_env = os.environ.get("ASUS_MARKETS_DB", "")
    if db_env and Path(db_env).exists():
        from asus_theye.dashboard.markets import markets_page

        (destino / "markets.html").write_text(markets_page(db_env), encoding="utf-8")
        gerados.append("markets.html")
    else:
        if not db_env:
            motivo = "markets: ASUS_MARKETS_DB ausente"
        else:
            motivo = f"markets: arquivo não encontrado ({db_env})"
        pulados.append(motivo)

    # --- index.html ----------------------------------------------------------
    items_html = "\n".join(f'  <li><a href="{p}">{p}</a></li>' for p in gerados)
    (destino / "index.html").write_text(_INDEX_TEMPLATE.format(items=items_html), encoding="utf-8")
    gerados.append("index.html")

    return {"gerados": gerados, "pulados": pulados}
