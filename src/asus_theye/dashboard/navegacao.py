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
# A VITRINE — só o que um cliente compraria, agrupado pelos DOIS produtos.
#
# O que saiu daqui e por quê: /projeto (percentual de fases), /mlops (corridas
# de ML) e /benchmark (benchmark quântico, legado de outro projeto) são
# telemetria INTERNA da obra. Continuam servidos e continuam versionados — mas
# quem abre a porta da frente tem de ver dois produtos, não a instrumentação de
# quem os construiu. Misturar as duas coisas foi o que fez a vitrine parecer um
# painel de engenharia em vez de um produto.
PAINEIS: tuple[tuple[str, str], ...] = (
    ("/", "início"),
    # --- Produto 1: THE EYE Markets — a previsão e a prova de que ela vale
    ("/mercados", "mercados"),
    ("/calibracao", "calibração"),
    # --- Produto 2: THE EYE Ledger — a trilha e como conferi-la sozinho
    ("/corrente", "corrente"),
    ("/evidencia", "evidência"),
    ("/api", "verificar"),
)

# Servidos, fora do menu público. Quem sabe a URL chega; ninguém tropeça neles.
PAINEIS_INTERNOS: tuple[tuple[str, str], ...] = (
    ("/projeto", "projeto"),
    ("/mlops", "mlops"),
    ("/benchmark", "benchmark"),
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


def destino(rota: str, *, estatico: bool = False) -> str:
    """Traduz a rota do servidor para o alvo certo em cada meio.

    No servidor, ``/projeto`` é a rota. No site exportado o arquivo é
    ``projeto.html`` — e depender do host resolver URL sem extensão é apostar
    numa configuração que pode não existir. Link morto em site publicado é pior
    do que site não publicado, então o destino é explícito.
    """
    if not estatico:
        return rota
    return "index.html" if rota == "/" else f"{rota.lstrip('/')}.html"


def barra(rota_atual: str = "", *, estatico: bool = False) -> str:
    """Devolve a barra de navegação, marcando *rota_atual* como página corrente.

    ``rota_atual`` vazia (ou desconhecida) simplesmente não marca ninguém — a
    barra continua útil, o que é melhor do que marcar o item errado.

    ``estatico=True`` emite caminhos de arquivo, para o site exportado.
    """
    itens = []
    for rota, rotulo in PAINEIS:
        atual = ' aria-current="page"' if rota == rota_atual else ""
        alvo = destino(rota, estatico=estatico)
        itens.append(f'<a href="{html.escape(alvo)}"{atual}>{html.escape(rotulo)}</a>')
    return f'<nav class="the-eye">{"".join(itens)}</nav>'


# O aviso que faltava. O produto é PT-BR, chama-se "mercados preditivos", exibe
# "contrato" e "liquidado", e se compara a uma bolsa de dinheiro real — mas NÃO
# tem saldo, carteira, livro de ordens nem pagamento em lugar nenhum do código.
# A declaração é verdadeira e gratuita, e sem ela um visitante pode confundir a
# plataforma com aposta de quota fixa, que no Brasil é atividade regulada.
#
# A frase já existia enterrada num docstring de markets/regra.py, onde nenhum
# usuário lê. Aqui ela vai para a tela.
AVISO = (
    "Isto <strong>não é aconselhamento financeiro</strong> e <strong>não é casa de apostas</strong>. "
    "Não há dinheiro, saldo, contraparte, ordem de compra ou pagamento — nenhum valor é movimentado. "
    "As probabilidades são estimativas próprias, publicadas antes do fato e resolvidas contra fonte "
    "oficial nomeada. Um mercado tem regra verificável; uma aposta tem alguém decidindo depois quem ganhou."
)

CSS_AVISO = """
footer.the-eye{margin:36px 0 0;padding:14px 16px;border-top:1px solid #253149;
color:#9aa8bd;font-size:.78rem;line-height:1.55;max-width:90ch}
footer.the-eye strong{color:#e9f0ff}
"""


def rodape() -> str:
    """Aviso de escopo, injetado em todos os painéis."""
    return f'<footer class="the-eye">{AVISO}</footer>'
