# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Barra de navegação compartilhada — o que amarra os painéis num site só.

Antes disto cada painel era uma ilha: quem abrisse ``/projeto`` não tinha como
descobrir que ``/corrente`` existe. A barra é HTML puro, sem dependência e sem
estado; cada painel a injeta no próprio shell passando a própria rota, para que
o item corrente apareça marcado.

O CSS mora aqui junto com o markup de propósito: os painéis já têm seus estilos
inline, e duplicar as regras da barra em oito arquivos seria a forma mais rápida
de elas divergirem.
"""

from __future__ import annotations

import html

# (rota, rótulo) — a ordem é a da jornada: o que é o produto, depois a prova,
# depois os bastidores. Rotas que não existem no servidor não entram aqui.
PAINEIS: tuple[tuple[str, str], ...] = (
    ("/", "início"),
    ("/mercados", "mercados"),
    ("/evidencia", "evidência"),
    ("/corrente", "corrente"),
    ("/projeto", "projeto"),
    ("/benchmark", "benchmark"),
    ("/mlops", "mlops"),
    ("/api", "api"),
)

CSS_NAV = """
nav.the-eye{display:flex;flex-wrap:wrap;gap:2px;margin:0 0 28px;padding:6px;
background:#101725;border:1px solid #253149;border-radius:12px}
nav.the-eye a{color:#9aa8bd;text-decoration:none;padding:8px 14px;border-radius:8px;
font-size:.86rem;letter-spacing:.03em;white-space:nowrap}
nav.the-eye a:hover{color:#e9f0ff;background:#1b2436}
nav.the-eye a[aria-current="page"]{color:#080d16;background:#67e8f9;font-weight:600}
@media (max-width:640px){nav.the-eye a{padding:7px 10px;font-size:.8rem}}
"""


def barra(rota_atual: str = "") -> str:
    """Devolve a barra de navegação, marcando *rota_atual* como página corrente.

    ``rota_atual`` vazia (ou desconhecida) simplesmente não marca ninguém — a
    barra continua útil, o que é melhor do que marcar o item errado.
    """
    itens = []
    for rota, rotulo in PAINEIS:
        atual = ' aria-current="page"' if rota == rota_atual else ""
        itens.append(f'<a href="{html.escape(rota)}"{atual}>{html.escape(rotulo)}</a>')
    return f'<nav class="the-eye">{"".join(itens)}</nav>'
