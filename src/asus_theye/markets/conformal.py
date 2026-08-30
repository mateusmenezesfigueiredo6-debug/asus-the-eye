# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inferência conformal: intervalo com cobertura garantida, sem supor distribuição.

É a peça que transforma "acho que 48%" em "entre 44% e 52%, e essa faixa acerta
em pelo menos 90% das vezes". Sem ela, uma meta de assertividade não tem como ser
verificada — número pontual não erra nem acerta, só fica perto ou longe.

POR QUE ESTA TÉCNICA E NÃO OUTRA. Em 2024, Zheng, Li, Song & Jiang combinaram
estimação em áreas pequenas com inferência conformal e **acertaram 44 de 44
estados** na eleição americana, reproduzindo o Colégio Eleitoral exato, enquanto
a média simples de pesquisas e o FiveThirtyEight erraram Michigan, Pensilvânia e
Wisconsin (arXiv:2511.03555, acesso aberto). O que faz a técnica servir para nós
não é o resultado dela lá — é a propriedade: **cobertura garantida sem supor
distribuição nenhuma**. Não precisamos alegar que o erro é gaussiano, e não
precisamos de milhares de observações para que a garantia valha.

A GARANTIA, dita com precisão. Com ``n`` pontos de calibração e nível ``alpha``,
a cobertura é **pelo menos** ``1 - alpha``, e no máximo ``1 - alpha + 1/(n+1)``.
Vale para qualquer distribuição, desde que os pontos de calibração e o ponto novo
sejam permutáveis entre si.

────────────────────────────────────────────────────────────────────────────
O PREÇO QUE PAGAMOS, E QUE ESTE MÓDULO SE RECUSA A ESCONDER

A granularidade da cobertura é ``1/(n+1)``. Com os sete candidatos de 2022 como
calibração, ``n = 7`` e o passo é **12,5%**. Na prática:

    alpha pedido 0,05 (95%)  ->  cobertura real garantida: 87,5%
    alpha pedido 0,10 (90%)  ->  cobertura real garantida: 87,5%

Não existe faixa de 95% com sete pontos de calibração. Pedir uma e receber um
número seria a mentira mais elegante possível — teria a forma de estatística e o
conteúdo de chute. :func:`cobertura_efetiva` calcula o que de fato se obtém, e
:func:`intervalo` avisa sempre que o pedido não pode ser honrado.

Para chegar a 95% de verdade seriam necessários **19 pontos** de calibração. Hoje
temos sete. Isso é um fato sobre a quantidade de eleições presidenciais
brasileiras já ocorridas com dado digital utilizável, não um defeito de código, e
a saída é acumular calibração — não afrouxar a régua.
────────────────────────────────────────────────────────────────────────────

A PERMUTABILIDADE É A HIPÓTESE QUE PODE QUEBRAR, e vale mais do que a
matemática. A garantia exige que o caso novo seja intercambiável com os de
calibração. Um candidato de 2026 é intercambiável com um de 2022? **Provavelmente
não**: Bolsonaro não é candidato, entraram dois nativos digitais, e duas famílias
de sinal deixaram de existir (X fechou o acesso gratuito em fev/2026, Reddit
passou a exigir OAuth). :func:`intervalo` aceita ``permutavel=False`` para marcar
o resultado como **indicativo, não garantido** — porque cobertura anunciada sob
hipótese violada é pior que nenhuma cobertura: dá confiança onde não há.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class ConformalError(RuntimeError):
    """Recusa produzir intervalo. Nunca devolve faixa sem garantia declarada."""


def cobertura_efetiva(n: int, alpha: float) -> float:
    """A cobertura que de fato se obtém com ``n`` pontos de calibração.

    O quantil conformal usa o índice ``ceil((n+1)(1-alpha))``. Quando esse índice
    passa de ``n``, não há ponto de calibração suficiente para sustentar o nível
    pedido, e a cobertura fica limitada a ``n/(n+1)``.
    """
    if n < 1:
        raise ConformalError("não há pontos de calibração")
    if not 0 < alpha < 1:
        raise ConformalError(f"alpha fora de (0,1): {alpha}")
    indice = math.ceil((n + 1) * (1 - alpha))
    return min(indice, n) / (n + 1)


def pontos_necessarios(alpha: float) -> int:
    """Quantos pontos de calibração são precisos para honrar ``alpha``.

    Para 95% exige 19; para 90%, 9. É a conta que diz se uma meta é alcançável
    hoje ou se depende de acumular histórico.
    """
    if not 0 < alpha < 1:
        raise ConformalError(f"alpha fora de (0,1): {alpha}")
    return math.ceil(1 / alpha) - 1


@dataclass(frozen=True)
class Intervalo:
    """Uma faixa e a verdade sobre o quanto ela vale."""

    centro: float
    baixo: float
    alto: float
    #: Cobertura pedida por quem chamou.
    alpha_pedido: float
    #: Cobertura que a matemática entrega com o n disponível.
    cobertura_garantida: float
    n_calibracao: int
    #: False quando a hipótese de permutabilidade foi declarada violada.
    garantia_valida: bool
    aviso: str = ""

    @property
    def largura(self) -> float:
        return self.alto - self.baixo

    def __str__(self) -> str:
        marca = "" if self.garantia_valida else "  [INDICATIVO — garantia não vale]"
        return (
            f"{self.centro*100:.2f}%  [{self.baixo*100:.2f}% .. {self.alto*100:.2f}%]  "
            f"cobertura {self.cobertura_garantida*100:.1f}% (n={self.n_calibracao}){marca}"
        )


def _quantil_conformal(scores: list[float], alpha: float) -> float:
    """Quantil conformal dos resíduos de calibração.

    Usa ``ceil((n+1)(1-alpha))``-ésimo menor score, não o percentil comum: é
    esse ajuste de ``+1`` que produz a garantia em amostra finita. Trocar por
    ``numpy.quantile`` daria um número parecido e destruiria a propriedade.
    """
    n = len(scores)
    ordenados = sorted(scores)
    indice = math.ceil((n + 1) * (1 - alpha))
    if indice > n:
        # Sem ponto suficiente: usa o maior resíduo observado e quem chama é
        # avisado de que a cobertura real ficou abaixo do pedido.
        return ordenados[-1]
    return ordenados[indice - 1]


def intervalo(
    centro: float,
    residuos_de_calibracao: list[float],
    *,
    alpha: float = 0.10,
    permutavel: bool = True,
    limitar_em_zero_um: bool = True,
) -> Intervalo:
    """Faixa em torno de ``centro`` com cobertura conformal.

    ``residuos_de_calibracao`` são os erros absolutos observados em casos cujo
    desfecho já se conhece — para nós, ``|previsto − real|`` de cada candidato em
    eleição encerrada.

    ``permutavel=False`` marca o resultado como indicativo. Use sempre que o caso
    novo não for intercambiável com a calibração: campo eleitoral diferente,
    fontes de sinal que mudaram, regra do jogo alterada.
    """
    if not residuos_de_calibracao:
        raise ConformalError(
            "sem resíduos de calibração — não existe intervalo honesto sem "
            "histórico de erro; devolver uma faixa aqui seria inventá-la"
        )
    if any(r < 0 for r in residuos_de_calibracao):
        raise ConformalError("resíduo negativo — devem ser erros absolutos")
    if not math.isfinite(centro):
        raise ConformalError(f"centro não finito: {centro}")

    n = len(residuos_de_calibracao)
    q = _quantil_conformal(residuos_de_calibracao, alpha)
    cobertura = cobertura_efetiva(n, alpha)

    avisos = []
    if cobertura < 1 - alpha - 1e-9:
        avisos.append(
            f"pedido {(1-alpha)*100:.0f}% mas só há {n} pontos de calibração; "
            f"a cobertura garantida é {cobertura*100:.1f}%. "
            f"Para {(1-alpha)*100:.0f}% seriam necessários {pontos_necessarios(alpha)} pontos."
        )
    if not permutavel:
        avisos.append(
            "permutabilidade declarada VIOLADA — o caso novo não é intercambiável "
            "com a calibração. A faixa é indicativa; a garantia matemática não vale."
        )
    if n < 5:
        avisos.append(f"calibração muito curta ({n} pontos): a faixa é instável")

    baixo, alto = centro - q, centro + q
    if limitar_em_zero_um:
        baixo, alto = max(0.0, baixo), min(1.0, alto)

    return Intervalo(
        centro=centro, baixo=baixo, alto=alto,
        alpha_pedido=alpha, cobertura_garantida=cobertura,
        n_calibracao=n, garantia_valida=permutavel,
        aviso=" | ".join(avisos),
    )


def cobertura_observada(
    intervalos: list[Intervalo], reais: list[float]
) -> float:
    """Fração dos casos reais que caíram dentro da faixa. A prova empírica.

    A garantia conformal é teórica; isto é a verificação. Divergência grande
    entre garantida e observada é sinal de que a permutabilidade quebrou — e é
    assim que se descobre, sem esperar alguém desconfiar.
    """
    if len(intervalos) != len(reais):
        raise ConformalError(
            f"{len(intervalos)} intervalos para {len(reais)} resultados"
        )
    if not intervalos:
        raise ConformalError("nada a verificar")
    dentro = sum(1 for i, r in zip(intervalos, reais) if i.baixo <= r <= i.alto)
    return dentro / len(intervalos)
