# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Modelo eleitoral de 2026 — construído da literatura, sem herdar parâmetro.

Substitui a primeira tentativa, que aplicava a 2026 uma inclinação ajustada nos
dados de 2022. O titular recusou isso duas vezes, e tinha razão nas duas: *"não
vamos usar o mesmo algoritmo, já mudou — temos que mudar junto."* A demonstração
do porquê foi didática: o beta de 8,5 medido em 2022, aplicado ao campo de 2026,
deu **97,8% de chance a um candidato com 1,4% do tempo de TV**. Nenhuma exceção
foi levantada. O número saiu limpo e era absurdo.

────────────────────────────────────────────────────────────────────────────
O QUE A LITERATURA IMPÕE, E COMO CADA ITEM VIROU DESENHO

**Estrutura composicional, não logit binário.** Stoetzer, Neunhoeffer, Gschwend,
Munzert & Sternberg (Zurique/Mannheim/Hertie, 2019) obtiveram RMSE de 1,88 p.p.
na Alemanha de 2017 com regressão de Dirichlet. O contraponto é o modelo do
*The Economist* (Heidemanns, Gelman & Morris, Columbia), que **declara por
escrito** não comportar terceiros partidos: é limitação de forma funcional, não
de ajuste. Com treze candidatos, dois turnos e federações, só a via composicional
serve. Aqui isso aparece como trabalho em log-razão centrada.

**Simples vence neste regime.** As M-Competitions são o maior benchmark público
de previsão que existe, e o achado é consistente: sofisticação só compensou a
partir da M5, com milhares de séries. Treze candidatos e uma eleição de
referência é regime M1–M4. Este modelo é deliberadamente raso.

**Encolhimento em vez de parâmetro ajustado.** É a peça que resolve a ordem do
titular. Sem calibração do ciclo corrente, não existe inclinação honesta a
aplicar — e a resposta da estatística para "estimar com pouca informação" não é
inventar um coeficiente, é **encolher em direção ao prior** (James-Stein;
Efron & Morris). Quanto menos evidência do ciclo, mais o modelo se aproxima da
distribuição neutra. A força do encolhimento sai da contagem de evidência, não
da escolha de ninguém.

**Pesos de coeficientes PUBLICADOS, não ajustados por mim.** Ajustar peso nos
mesmos dados que se quer prever é como o beta de 8,5 nasceu. Aqui cada família
entra com peso ancorado em efeito medido por terceiros, com citação:

    Fernandes & Fernandes (2019), *Organizações & Sociedade*
        +10 p.p. de crescimento no consumo de energia -> +1,49 p.p. ao incumbente
    Zucco (2013), *AJPS*
        Bolsa Família e voto no incumbente, três eleições presidenciais
    Speck & Cervi (2016), *Dados*
        tempo de HGPE, beta padronizado 0,106 (N=13.038, R²=0,54);
        quarto fator, atrás de dinheiro, memória eleitoral e competitividade
    Yasseri & Bright (2016), *EPJ Data Science*
        visualização ABSOLUTA dá pouco insight; a VARIAÇÃO informa

**Sem LLM simulando eleitorado.** Wang et al. (CUHK/NTU) mediram viés
sistemático — GPT-4o superestima um lado em 1,5 p.p. e subestima o outro em
3,5 p.p. (p<0,001) — e injetar notícia real **piora**. Fica proibido por escrito,
não por bom senso.

**Verificação antes de acreditar.** Nenhum número sai daqui sem skill score
contra baseline (``verificacao.py``) e sem faixa conformal (``conformal.py``).
Brier sozinho não é resultado.
────────────────────────────────────────────────────────────────────────────

O QUE ESTE MODELO NÃO FAZ: não usa pesquisa de opinião, não pergunta nada a
ninguém, não simula eleitor, não empresta parâmetro de outro ciclo e não devolve
número sem declarar o quanto ele vale.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

from asus_theye.markets.modelo_eleitoral import ModeloError, clr, de_clr, normalizar


@dataclass(frozen=True)
class Evidencia:
    """Uma família de sinal, com o peso ancorado em literatura publicada."""

    nome: str
    valores: dict[str, float]
    #: Peso relativo. Justificado por efeito medido por TERCEIROS — nunca
    #: ajustado nos dados que se quer prever.
    peso: float
    #: A citação que sustenta o peso. Exigida: peso sem fonte é peso escolhido,
    #: e peso escolhido é a porta de entrada do sobreajuste.
    fonte_do_peso: str
    vies_declarado: str = ""

    def __post_init__(self) -> None:
        if self.peso <= 0:
            raise ModeloError(f"{self.nome!r}: peso deve ser positivo")
        if not self.fonte_do_peso.strip():
            raise ModeloError(
                f"{self.nome!r}: peso sem fonte. Um peso que ninguém mediu é um "
                "peso escolhido, e escolher peso olhando o resultado é o defeito "
                "que este modelo existe para não repetir."
            )
        if not self.valores:
            raise ModeloError(f"{self.nome!r}: sem valores")


@dataclass
class Modelo2026:
    """Combina evidências em log-razão e encolhe conforme a ignorância."""

    candidatos: tuple[str, ...]
    evidencias: list[Evidencia] = field(default_factory=list)
    #: Quantos resultados reais DO CICLO CORRENTE já foram observados. Zero
    #: significa que nada foi verificado ainda — e o modelo encolhe ao máximo.
    observacoes_do_ciclo: int = 0
    #: Quantas observações seriam necessárias para confiar plenamente no sinal.
    #: Não é palpite: é a conta da inferência conformal — 19 pontos para
    #: sustentar 95% de cobertura (ver conformal.pontos_necessarios).
    observacoes_para_confianca: int = 19

    def __post_init__(self) -> None:
        if len(self.candidatos) < 2:
            raise ModeloError("é preciso pelo menos dois candidatos")
        if len(set(self.candidatos)) != len(self.candidatos):
            raise ModeloError("candidato repetido")
        if self.observacoes_do_ciclo < 0:
            raise ModeloError("contagem de observações negativa")

    @property
    def encolhimento(self) -> float:
        """Fração do sinal que é descartada em favor da distribuição neutra.

        1,0 = ignorância total, devolve distribuição uniforme. 0,0 = confiança
        plena no sinal. A conta é ``1 - n/N``: sem observação do ciclo, encolhe
        tudo; com N observações, não encolhe nada.

        É a peça que substitui o expoente ajustado. Em vez de amplificar o sinal
        com um número medido noutro mundo, o modelo **admite o que não sabe** e
        se aproxima do neutro na medida exata dessa ignorância.
        """
        return max(0.0, 1.0 - self.observacoes_do_ciclo / self.observacoes_para_confianca)

    def fatias(self, *, magnitude: bool = True) -> dict[str, float]:
        """Fatia de voto estimada. Soma 1.

        ``magnitude=True`` aplica o encolhimento à DISTÂNCIA entre candidatos —
        é o que sobra sem resultado eleitoral do ciclo para calibrar quanto
        confiar na escala. ``magnitude=False`` devolve a combinação bruta das
        evidências vivas, sem encolher: é a leitura que preserva ORDEM, que as
        evidências de hoje (atenção, tempo de TV) já sustentam mesmo sem
        resultado de 2026.

        O erro que esta assinatura corrige: encolher a distribuição para
        UNIFORME com evidência viva em mãos apagava a ordem junto com a
        magnitude — onze candidatos empatados em 9,09%, quando duas fontes
        atuais já diferenciam Bolsonaro e Lula do resto. `encolhimento` deveria
        vetar reaplicar o BETA de 2022 (que é o que o titular proibiu), não
        vetar toda leitura de evidência corrente.
        """
        if not self.evidencias:
            raise ModeloError("nenhuma evidência — o modelo não inventa distribuição")

        total = sum(e.peso for e in self.evidencias)
        combinado = {c: 0.0 for c in self.candidatos}
        for ev in self.evidencias:
            faltando = set(self.candidatos) - set(ev.valores)
            if faltando:
                raise ModeloError(
                    f"{ev.nome!r} não cobre {sorted(faltando)} — ausência não vira "
                    "zero, porque zero afirmaria que o candidato não tem nada"
                )
            coords = clr(normalizar({c: ev.valores[c] for c in self.candidatos}))
            # Escala comparável ANTES de ponderar. Sem isto, a família de maior
            # dispersão domina a média mesmo com pesos iguais — foi assim que um
            # candidato com 1,4% do tempo de TV saiu com 97,8%.
            escala = (sum(v * v for v in coords.values()) / len(coords)) ** 0.5
            if escala > 1e-9:
                coords = {c: v / escala for c, v in coords.items()}
            for c in self.candidatos:
                combinado[c] += ev.peso * coords[c] / total

        if not magnitude:
            return de_clr(combinado)

        # Encolhimento em direção ao neutro: no espaço log-razão, a distribuição
        # uniforme é a origem, então encolher é simplesmente multiplicar.
        fator = 1.0 - self.encolhimento
        return de_clr({c: v * fator for c, v in combinado.items()})

    def ordem(self) -> list[tuple[str, float]]:
        """Do maior para o menor. É a saída em que se confia mais.

        O sinal de atenção mostrou-se bom para ordenar e ruim para dimensionar;
        a ordem sobrevive ao encolhimento, a magnitude não.
        """
        return sorted(self.fatias().items(), key=lambda kv: -kv[1])

    def houve_segundo_turno(self) -> bool | None:
        """``None`` enquanto o modelo estiver encolhido demais para afirmar.

        Art. 77, §3º: eleito em primeiro turno quem tem MAIS da metade dos
        válidos. Com encolhimento alto o modelo tende ao uniforme, e uniforme
        nunca ultrapassa 50% com três ou mais candidatos — responder "sim" ali
        seria confundir ignorância com previsão de segundo turno.
        """
        if self.encolhimento > 0.5:
            return None
        return max(self.fatias().values()) <= 0.5

    def avisos(self, hoje: date | None = None) -> list[str]:
        """Tudo que o consumidor precisa saber antes de usar o número."""
        fora = [
            f"encolhimento {self.encolhimento:.0%} — o modelo viu "
            f"{self.observacoes_do_ciclo} de {self.observacoes_para_confianca} "
            "observações do ciclo corrente"
        ]
        if self.encolhimento >= 0.99:
            fora.append(
                "NENHUMA observação do ciclo: a saída está praticamente uniforme, "
                "e isso é honestidade, não falha. Sem resultado real de 2026 não "
                "existe base para afirmar magnitude — só ordem."
            )
        elif self.encolhimento > 0.5:
            fora.append(
                "encolhimento alto: use a ORDEM, não a magnitude. A distância "
                "entre candidatos ainda não tem sustentação medida."
            )
        for ev in self.evidencias:
            fora.append(f"{ev.nome}: peso {ev.peso:.2f} — {ev.fonte_do_peso}")
            if ev.vies_declarado:
                fora.append(f"{ev.nome}: {ev.vies_declarado}")
        if len(self.evidencias) < 2:
            fora.append(
                "família única de evidência — o backtest de 2022 mostrou que "
                "atenção sozinha erra por não enxergar estrutura partidária"
            )
        return fora

    def residuos_para_conformal(self) -> list[float]:
        """Resíduos disponíveis para calibrar faixa. Vazio até haver resultado.

        Existe para deixar explícito que **não temos** resíduos do ciclo de 2026,
        e que qualquer faixa produzida hoje sai de outro mundo — o que
        ``conformal.intervalo(..., permutavel=False)`` marca como indicativa.
        """
        return []
