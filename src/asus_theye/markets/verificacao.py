# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verificação de previsão probabilística, na escola da meteorologia.

A meteorologia é o campo mais maduro do mundo em previsão probabilística. O
Brier score nasceu ali em 1950; reliability diagram, CRPS, ensemble e a própria
noção de "sharpness sujeito a calibração" vieram todos de lá. Um meteorologista
sabe medir previsão probabilística melhor que qualquer outro profissional — e é
essa competência que falta a uma casa de previsão, independentemente do assunto.

Este módulo copia quatro práticas operacionais do ECMWF e do Met Office.

────────────────────────────────────────────────────────────────────────────
1. ERRO BRUTO SOZINHO NÃO SIGNIFICA NADA

É o erro que este arquivo existe para corrigir, e foi cometido aqui mesmo: um
Brier de 0,10 foi tratado como bom sem que ninguém perguntasse quanto um palpite
ingênuo faria no MESMO problema. Se prever "o incumbente vence", sem modelo
nenhum, já der 0,12, então 0,10 é quase nada — e um relatório que só mostrasse
0,10 estaria enganando quem o lê, sem mentir em nenhum número.

Meteorologista nenhum reporta erro sem baseline ao lado. :func:`skill_score`
devolve a fração do erro do baseline que foi efetivamente eliminada: 0 significa
"não fez melhor que o burro", 1 significa perfeito, e negativo significa que o
modelo é PIOR que não ter modelo.

2. DECOMPOSIÇÃO DIZ QUAL PARTE ESTÁ RUIM

Murphy (1973) decompôs o Brier em três parcelas:

    Brier = Confiabilidade − Resolução + Incerteza

**Confiabilidade** (menor é melhor): quando você diz 70%, acontece 70% das
vezes? É calibração pura. **Resolução** (maior é melhor): suas previsões
distinguem casos, ou você diz sempre a mesma coisa? **Incerteza**: dificuldade
intrínseca do problema, que não depende de você.

Isso importa porque os dois defeitos exigem remédios opostos. Confiabilidade
ruim se conserta recalibrando. Resolução ruim significa que falta SINAL, e
recalibrar não resolve — é preciso dado novo. Um score agregado não distingue os
dois, e quem só olha o agregado tenta o remédio errado.

3. EVENTO RARO EXIGE REGRA PONDERADA

Lerch et al. (2017) chamam de "dilema do previsor": avaliar um modelo apenas nos
casos extremos premia sistematicamente quem exagera na previsão de extremos.
Aplicado a nós: julgar o modelo só pelas viradas eleitorais recompensaria quem
grita virada toda semana. :func:`brier_ponderado` aplica peso sem cair nisso.

4. O PAINEL É PRÉ-REGISTRADO

Como se mede é declarado ANTES de medir. É a mesma disciplina do "critério
declarado antes" que já está em cada mercado do preview — e a razão é a mesma:
escolher a métrica depois de ver o resultado é escolher o resultado.
────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


class VerificacaoError(RuntimeError):
    """Recusa produzir métrica. Score sobre dado insuficiente engana."""


def brier(previsoes: list[float], desfechos: list[bool]) -> float:
    """Erro quadrático médio da probabilidade. Menor é melhor; 0 é perfeito."""
    if len(previsoes) != len(desfechos):
        raise VerificacaoError(f"{len(previsoes)} previsões para {len(desfechos)} desfechos")
    if not previsoes:
        raise VerificacaoError("nada a verificar")
    if any(not 0.0 <= p <= 1.0 for p in previsoes):
        raise VerificacaoError("probabilidade fora de [0,1]")
    return sum((p - float(d)) ** 2 for p, d in zip(previsoes, desfechos)) / len(previsoes)


def climatologia(desfechos: list[bool]) -> float:
    """A previsão ingênua: a taxa-base histórica, igual para todos os casos.

    Em meteorologia se chama climatologia — "chove 30% dos dias de março, então
    minha previsão é 30% todo dia de março". É o baseline mínimo que qualquer
    modelo precisa bater para justificar a própria existência.
    """
    if not desfechos:
        raise VerificacaoError("sem desfechos para calcular a taxa-base")
    return sum(desfechos) / len(desfechos)


def skill_score(previsoes: list[float], desfechos: list[bool], *, baseline: float | None = None) -> float:
    """Fração do erro do baseline que o modelo eliminou.

    ``1 - Brier_modelo / Brier_baseline``. Zero é "não fez melhor que o burro";
    negativo é PIOR que não ter modelo. Sem ``baseline``, usa a climatologia dos
    próprios desfechos.

    Este é o número que deve aparecer ao lado de todo Brier que esta casa
    publicar. Brier sozinho não é resultado; é metade de um resultado.
    """
    b_modelo = brier(previsoes, desfechos)
    taxa = climatologia(desfechos) if baseline is None else baseline
    b_base = brier([taxa] * len(desfechos), desfechos)
    if b_base == 0:
        raise VerificacaoError(
            "o baseline é perfeito (todos os desfechos iguais) — não há skill a "
            "medir. Isso não é mérito do modelo nem defeito: o problema não "
            "tinha incerteza nenhuma."
        )
    return 1.0 - b_modelo / b_base


@dataclass(frozen=True)
class Decomposicao:
    """Brier repartido em confiabilidade, resolução e incerteza."""

    brier: float
    confiabilidade: float   # menor é melhor — é calibração
    resolucao: float        # maior é melhor — é poder de discriminar
    incerteza: float        # dificuldade intrínseca, não depende do modelo
    n_faixas: int

    @property
    def residuo(self) -> float:
        """A variância DENTRO das faixas — e não é erro de arredondamento.

        A identidade ``Brier = confiabilidade − resolução + incerteza`` fecha
        exatamente quando todas as previsões de uma faixa são idênticas. Com
        previsões contínuas agrupadas, sobra a dispersão interna de cada faixa,
        e é ela que aparece aqui.

        Isto foi documentado errado na primeira versão ("arredondamento"), e um
        teste que exigia resíduo zero falhou — corretamente. A grandeza é real e
        tem leitura útil: resíduo grande significa que as faixas estão largas
        demais para o formato das previsões, e vale aumentar ``n_faixas``.
        """
        return self.brier - (self.confiabilidade - self.resolucao + self.incerteza)

    def diagnostico(self) -> str:
        """Diz qual remédio aplicar — e são remédios opostos."""
        partes = [
            f"Brier {self.brier:.4f} = confiabilidade {self.confiabilidade:.4f} "
            f"− resolução {self.resolucao:.4f} + incerteza {self.incerteza:.4f}"
        ]
        if self.confiabilidade > 0.02:
            partes.append(
                "CALIBRAÇÃO RUIM: quando o modelo diz 70%, não acontece 70% das "
                "vezes. Remédio é recalibrar — não precisa de dado novo."
            )
        if self.resolucao < 0.02:
            partes.append(
                "RESOLUÇÃO BAIXA: o modelo quase não distingue um caso do outro. "
                "Recalibrar NÃO resolve — falta sinal, e sinal só vem de dado novo."
            )
        if self.confiabilidade <= 0.02 and self.resolucao >= 0.02:
            partes.append("calibração e discriminação em ordem")
        return " | ".join(partes)


def decompor(previsoes: list[float], desfechos: list[bool], *, n_faixas: int = 10) -> Decomposicao:
    """Decomposição de Murphy (1973). Exige agrupar em faixas de probabilidade.

    O agrupamento é o preço da decomposição: previsões contínuas precisam ser
    discretizadas para que se possa perguntar "das vezes que disse ~70%, quantas
    aconteceram?". Faixas demais deixam cada uma com um caso só, e a
    confiabilidade vira ruído; faixas de menos escondem descalibração dentro da
    mesma faixa.
    """
    if len(previsoes) != len(desfechos):
        raise VerificacaoError("contagens diferentes")
    n = len(previsoes)
    if n < n_faixas:
        raise VerificacaoError(
            f"{n} previsões para {n_faixas} faixas — cada faixa ficaria com menos "
            "de um caso, e a decomposição viraria ruído com aparência de número"
        )
    taxa_geral = climatologia(desfechos)
    grupos: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for p, d in zip(previsoes, desfechos):
        grupos[min(int(p * n_faixas), n_faixas - 1)].append((p, d))

    conf = res = 0.0
    for itens in grupos.values():
        nk = len(itens)
        p_medio = sum(p for p, _ in itens) / nk
        o_medio = sum(float(d) for _, d in itens) / nk
        conf += nk * (p_medio - o_medio) ** 2
        res += nk * (o_medio - taxa_geral) ** 2
    return Decomposicao(
        brier=brier(previsoes, desfechos),
        confiabilidade=conf / n,
        resolucao=res / n,
        incerteza=taxa_geral * (1 - taxa_geral),
        n_faixas=len(grupos),
    )


def brier_ponderado(
    previsoes: list[float], desfechos: list[bool], pesos: list[float]
) -> float:
    """Brier com peso por caso, para quando alguns eventos importam mais.

    Existe para o "dilema do previsor" (Lerch et al., 2017): filtrar a avaliação
    apenas para os casos extremos premia sistematicamente quem exagera na
    previsão de extremos, porque quem grita virada toda semana acerta todas as
    viradas. Ponderar preserva todos os casos e ainda dá mais peso ao que
    importa — filtrar, não.
    """
    if not (len(previsoes) == len(desfechos) == len(pesos)):
        raise VerificacaoError("previsões, desfechos e pesos têm tamanhos diferentes")
    if not previsoes:
        raise VerificacaoError("nada a verificar")
    if any(w < 0 for w in pesos):
        raise VerificacaoError("peso negativo")
    soma = sum(pesos)
    if soma <= 0:
        raise VerificacaoError("todos os pesos são zero")
    return sum(w * (p - float(d)) ** 2 for p, d, w in zip(previsoes, desfechos, pesos)) / soma


def diagrama_de_confiabilidade(
    previsoes: list[float], desfechos: list[bool], *, n_faixas: int = 10
) -> list[dict]:
    """Os pontos do reliability diagram: previsto vs. observado, por faixa.

    A leitura é direta: num modelo bem calibrado, ``previsto`` e ``observado``
    andam juntos. Faixa em que o previsto é maior que o observado é excesso de
    confiança; o contrário é timidez.
    """
    if len(previsoes) != len(desfechos):
        raise VerificacaoError("contagens diferentes")
    grupos: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for p, d in zip(previsoes, desfechos):
        grupos[min(int(p * n_faixas), n_faixas - 1)].append((p, d))
    fora = []
    for faixa in sorted(grupos):
        itens = grupos[faixa]
        nk = len(itens)
        fora.append({
            "faixa": f"{faixa/n_faixas:.0%}–{(faixa+1)/n_faixas:.0%}",
            "n": nk,
            "previsto": sum(p for p, _ in itens) / nk,
            "observado": sum(float(d) for _, d in itens) / nk,
            # Faixa com poucos casos não sustenta conclusão nenhuma.
            "confiavel": nk >= 5,
        })
    return fora


def painel(previsoes: list[float], desfechos: list[bool], *, n_faixas: int = 10) -> dict:
    """O painel de verificação completo. Pré-registrado: mede-se sempre assim.

    Declarar a métrica antes de ver o resultado é a mesma disciplina do "critério
    declarado antes" de cada mercado — e pela mesma razão: escolher a métrica
    depois de ver o resultado é escolher o resultado.
    """
    b = brier(previsoes, desfechos)
    taxa = climatologia(desfechos)
    saida = {
        "n": len(previsoes),
        "brier": b,
        "climatologia": taxa,
        "brier_do_baseline": brier([taxa] * len(desfechos), desfechos),
        "acaso_puro": 0.25,
    }
    try:
        saida["skill_score"] = skill_score(previsoes, desfechos)
    except VerificacaoError as erro:
        saida["skill_score"] = None
        saida["skill_indisponivel"] = str(erro)
    try:
        d = decompor(previsoes, desfechos, n_faixas=n_faixas)
        saida["decomposicao"] = {
            "confiabilidade": d.confiabilidade,
            "resolucao": d.resolucao,
            "incerteza": d.incerteza,
            "diagnostico": d.diagnostico(),
        }
    except VerificacaoError as erro:
        saida["decomposicao"] = None
        saida["decomposicao_indisponivel"] = str(erro)
    return saida
