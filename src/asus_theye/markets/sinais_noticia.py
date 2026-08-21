# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sinal de cobertura noticiosa — a trilha que não passa pelo consenso.

Este módulo produz a **segunda** probabilidade de cada mercado. A primeira vem
do boletim Focus e é o que a plataforma sempre publicou; esta vem do tom da
cobertura de imprensa, e existe para responder a uma pergunta que hoje não tem
resposta: *a plataforma sabe alguma coisa que o consenso não sabe?*

**A independência é estrutural, não uma promessa.** Este arquivo não importa
nada de :mod:`asus_theye.markets.sinais_ipca`, não lê o Focus, não lê o IPCA-15
— que é insumo do próprio Focus e irmão metodológico do índice que liquida o
contrato. Se um dia alguém acrescentar aqui um sinal que passe pelo consenso, a
comparação entre as duas trilhas perde o sentido inteiro, e o teste que compara
as fontes das duas quebra.

**A expectativa, registrada antes de qualquer resultado.** Tom de notícia é
sinal fraco e ruidoso para inflação. É esperado que **não supere** o Focus. A
razão de existir não é vencer — é poder **medir**. Hoje a plataforma não pode
afirmar nada sobre desempenho próprio; com as duas trilhas seladas antes do
desfecho, ela passa a poder afirmar o que os dados mostrarem, inclusive
paridade, que é resultado publicável.

**A limitação desta primeira versão, dita antes que alguém descubra.** O tom é
medido por PAÍS, não por indicador. Isso significa que hoje as três perguntas
abertas — inflação, juros e câmbio — recebem a **mesma** probabilidade da trilha
própria. É uma fraqueza real: um sinal que não distingue as perguntas não pode
estar informativamente certo sobre todas ao mesmo tempo.

Está assim de propósito, e não escondido: a versão que distingue exige filtrar
por tema dentro do arquivo de eventos, o que é trabalho maior e sem amostra
para validar. Publicar a versão simples com a limitação declarada é melhor do
que segurar até ficar perfeita — porque o relógio da calibração só anda com
contratos liquidados, e cada mês parado é um mês perdido.

**A direção do sinal, e por que esta.** Cobertura de tom mais negativo que o
usual acompanha pressão econômica noticiada — reajuste, escassez, crise. Para
uma pergunta do tipo "o indicador passa do limiar?", tom negativo empurra para
"sim". É hipótese declarada, não lei: quando houver amostra, o painel de
calibração vai dizer se ela se sustenta. Se não se sustentar, isso também é
resultado, e sai publicado.
"""

from __future__ import annotations

from typing import Any

from asus_theye.markets.fonte_gdelt import CoberturaNoticiosa, FonteGDELTError, cobertura
from asus_theye.markets.gerador import Probabilidade, Sinal, gerar_probabilidade

# Peso deliberadamente BAIXO. O sinal do Focus pesa 20; este pesa 6, porque tom
# de notícia é evidência mais fraca que a mediana de cem instituições. Peso
# alto aqui produziria convicção que o dado não sustenta.
PESO_NOTICIA = 6.0

# O tom médio global do GDELT orbita levemente negativo. O corte é a referência
# a partir da qual "mais negativo que o normal" começa — declarado aqui, e
# revisável quando houver amostra que justifique outro número.
TOM_DE_REFERENCIA = -3.0

# País de interesse, em FIPS 10-4.
PAIS_PADRAO = "BR"


class SinaisNoticiaError(RuntimeError):
    """Cobertura indisponível ou malformada. Sempre levanta."""


def sinal_de_cobertura(observacao: CoberturaNoticiosa) -> Sinal | None:
    """Converte a cobertura num sinal — ou ``None`` quando não há o que dizer.

    Amostra abaixo do mínimo devolve ``None``, e não um sinal fraco: poucos
    eventos numa janela de quinze minutos não são evidência de nada, e fingir
    que são contaminaria a trilha inteira.
    """
    if not observacao.suficiente:
        return None

    mais_negativo = observacao.tom_medio < TOM_DE_REFERENCIA
    return Sinal(
        direcao="sim" if mais_negativo else "nao",
        peso=PESO_NOTICIA,
        fonte=(
            f"{observacao.atribuicao} — tom médio {observacao.tom_medio:+.4f} em "
            f"{observacao.eventos} evento(s) sobre {observacao.pais_fips} "
            f"(referência {TOM_DE_REFERENCIA:+.1f}; arquivo {observacao.arquivo}, "
            f"md5 {observacao.md5_do_arquivo[:12]}…)"
        ),
    )


def probabilidade_por_noticia(
    mes_referencia: str,  # noqa: ARG001 - a trilha é diária; o mês entra para simetria de assinatura
    limiar: float,  # noqa: ARG001 - o tom não se compara ao limiar; a direção vem da referência
    *,
    pais_fips: str = PAIS_PADRAO,
    transport: Any = None,
) -> Probabilidade:
    """A probabilidade da trilha própria — sem tocar no consenso em ponto algum.

    A assinatura espelha a dos demais geradores (``mes_referencia``, ``limiar``)
    para que o laço de reprecificação trate todas as trilhas igual. Os dois
    argumentos não são usados aqui de propósito: o tom da cobertura não se
    compara ao limiar do contrato — a direção vem do desvio em relação ao tom de
    referência. Manter a assinatura e declarar o não-uso é mais honesto do que
    inventar uma relação que não existe.

    Sem cobertura suficiente, devolve exatamente 0,50 com ``max_uncertainty`` —
    a mesma degradação honesta do resto da casa.
    """
    try:
        observacao = cobertura(pais_fips, transport=transport)
    except FonteGDELTError as erro:
        raise SinaisNoticiaError(f"cobertura noticiosa indisponível: {erro}") from erro

    sinal = sinal_de_cobertura(observacao)
    return gerar_probabilidade([sinal] if sinal else [])
