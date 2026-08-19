"""Exporta os painéis do dashboard como HTML estático em disco."""

from __future__ import annotations

import html
import os
from pathlib import Path

from asus_theye.dashboard.benchmark import benchmark_page
from asus_theye.dashboard.evidencia import evidencia_page
from asus_theye.dashboard.markets import markets_page
from asus_theye.dashboard.projeto import projeto_page


def _escrever(destino: Path, nome: str, conteudo: str) -> str:
    caminho = destino / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)


def _index_page(paginas: list[str]) -> str:
    itens = "\n".join(
        f'<li><a href="{html.escape(nome)}">{html.escape(nome.replace(".html", "").title())}</a></li>'
        for nome in paginas
    )
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE — Dashboard estático</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:900px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em}}
p{{color:var(--muted)}}
ul{{list-style:none;padding:0;display:grid;gap:14px}}
li{{background:var(--panel);border:1px solid #253149;border-radius:12px}}
a{{display:block;padding:18px 20px;color:var(--accent);text-decoration:none}}
a:hover{{text-decoration:underline}}
</style></head><body><main><h1>DASHBOARD ESTÁTICO</h1>
<p>Páginas geradas localmente para inspeção e publicação posterior sob portão.</p>
<ul>{itens}</ul>
</main></body></html>"""


def exportar(destino: Path) -> dict[str, list[str]]:
    """Renderiza os painéis do dashboard em HTML estático no diretório informado."""

    destino.mkdir(parents=True, exist_ok=True)
    gerados = [
        _escrever(destino, "projeto.html", projeto_page()),
        _escrever(destino, "evidencia.html", evidencia_page()),
        _escrever(destino, "benchmark.html", benchmark_page()),
    ]
    pulados: list[str] = []

    markets_db = os.environ.get("ASUS_MARKETS_DB")
    if markets_db and Path(markets_db).exists():
        gerados.append(_escrever(destino, "markets.html", markets_page(markets_db)))
    else:
        pulados.append("markets.html (ASUS_MARKETS_DB ausente ou arquivo inexistente)")

    gerados.append(_escrever(destino, "index.html", _index_page([Path(caminho).name for caminho in gerados])))
    return {"gerados": gerados, "pulados": pulados}
