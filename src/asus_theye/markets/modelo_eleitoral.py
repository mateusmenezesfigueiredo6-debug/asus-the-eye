# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Modelo eleitoral: combina sinais observacionais em probabilidade calibrada.

Não pergunta nada a ninguém. Não tem população-alvo, plano amostral, questionário
nem entrevistador — os quatro elementos que a Res. TSE 23.600/2019 usa para
caracterizar "pesquisa de opinião pública". Lê dado que já existe: resultado
apurado, atenção pública medida e estrutura partidária publicada.

────────────────────────────────────────────────────────────────────────────
O QUE O BACKTEST CONTRA 2022 ENSINOU, E QUE DEFINE ESTE ARQUIVO

Medido em 30/08/2026 contra o boletim oficial do 1º turno, com corte duro na
véspera (nada posterior a 01/10/2022 entrou):

    sinal de atenção, sem transformação ......... 12,60 pp de erro médio
    com log-razão, fora da amostra .............. 3,30 pp
    acertou os dois do 2º turno, na ordem ....... sim

E o detalhe que importa mais que a média:

    LULA ............. previsto 49,07%  real 48,72%   (+0,35)
    JAIR BOLSONARO ... previsto 38,27%  real 43,46%   (-5,19)
    CIRO GOMES ....... previsto 11,41%  real  3,06%   (+8,36)  <-- o buraco
    SIMONE TEBET ..... previsto  0,87%  real  4,19%   (-3,31)  <-- o outro

Ciro tinha atenção demais para o voto que fez: figura midiática, muita
entrevista, muita polêmica, estrutura partidária fraca. Tebet tinha atenção de
menos: pouca visibilidade digital, mas MDB atrás e adesões tardias. **A atenção
não enxerga estrutura partidária** — e é exatamente aí que o modelo erra.

Daí a arquitetura: **um sinal nunca decide**. Cada família entra com seu peso, e
a combinação é feita no espaço log-razão.
────────────────────────────────────────────────────────────────────────────

POR QUE COMBINAÇÃO SIMPLES, E NÃO ALGO SOFISTICADO. As M-Competitions são o
maior benchmark público de previsão que existe, e o achado que importa aqui é
que **em regime de poucos dados o método simples ganha**. Foi só na M5, com
milhares de séries, que o aprendizado de máquina virou o jogo. Onze candidatos e
uma eleição de referência é o regime M1–M4, não o M5. Sofisticar aqui não
aumentaria assertividade — aumentaria variância, com a aparência de rigor.

POR QUE LOG-RAZÃO. Fatia de voto é dado composicional: soma 1 e vive num
simplex, onde média e regressão comuns não valem. A transformação log-razão
(Aitchison; Stoetzer et al., *Political Analysis* 2019) leva a composição para um
espaço onde somar e ponderar faz sentido, e traz de volta garantindo que o
resultado ainda soma 1. Também transforma "concentração" numa **inclinação**, que
é grandeza interpretável e regularizável — ao contrário do expoente de potência
que, ajustado direto, fugia para o limite da busca e denunciava sobreajuste.

────────────────────────────────────────────────────────────────────────────
A DATA DE VALIDADE — regra permanente do titular

    "O mundo muda, os algoritmos mudam. O motor tem que ser dinâmico."

Todo modelo daqui carrega ``calibrado_em`` e ``valido_para``. O ``beta`` medido
em 2022 vale como **forma** do erro (atenção comprime, voto concentra) e **não**
como valor, porque o campo eleitoral de 2026 não tem Bolsonaro, ganhou dois
candidatos nativos digitais e perdeu duas famílias de sinal — X fechou o acesso
gratuito em fev/2026 e o Reddit passou a exigir OAuth. Parâmetro congelado é
parâmetro errado esperando a hora de aparecer.

:meth:`Modelo.avisos` devolve o que está vencido. Quem consome decide o que fazer
com isso; o que o modelo não faz é ficar quieto.
────────────────────────────────────────────────────────────────────────────

O VIÉS QUE NÃO DÁ PARA CONSERTAR AQUI, só declarar. O leitorado da Wikipédia tem
escolaridade superior, é jovem, urbano, e homens geram cerca de 72% das
visualizações. As eleições brasileiras são decididas pelas classes C, D e E, das
quais 87% acessam a internet só pelo celular. Nenhum estudo publicado mede o
tamanho desse desvio. Por isso a atenção entra com peso **aprendido**, nunca
como estimador isolado, e o modelo declara o viés em vez de escondê-lo atrás de
uma probabilidade de aparência limpa.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date


class ModeloError(RuntimeError):
    """O modelo recusa produzir número. Nunca devolve palpite silencioso."""


def clr(composicao: dict[str, float], *, piso: float = 1e-6) -> dict[str, float]:
    """Log-razão centrada: leva uma composição para o espaço onde se soma.

    ``piso`` evita ``log(0)``. Fatia zerada é ausência de sinal, não
    impossibilidade — e tratá-la como impossibilidade eliminaria candidato do
    páreo por falta de dado, que é o oposto de medir.
    """
    if not composicao:
        raise ModeloError("composição vazia")
    if any(v < 0 for v in composicao.values()):
        raise ModeloError(f"composição com valor negativo: {composicao}")
    seguras = {k: max(v, piso) for k, v in composicao.items()}
    media_log = sum(math.log(v) for v in seguras.values()) / len(seguras)
    return {k: math.log(v) - media_log for k, v in seguras.items()}


def de_clr(coordenadas: dict[str, float]) -> dict[str, float]:
    """Volta do espaço log-razão para uma composição que soma 1."""
    if not coordenadas:
        raise ModeloError("coordenadas vazias")
    # Subtrair o máximo antes de exponenciar evita estouro quando a inclinação
    # é alta — com beta ~8 e coordenadas ~5, exp(40) já é grande demais.
    teto = max(coordenadas.values())
    expo = {k: math.exp(v - teto) for k, v in coordenadas.items()}
    soma = sum(expo.values())
    if soma <= 0 or not math.isfinite(soma):
        raise ModeloError("composição degenerada ao voltar do log-razão")
    return {k: v / soma for k, v in expo.items()}


def normalizar(valores: dict[str, float]) -> dict[str, float]:
    """Fatias que somam 1. Soma zero é indisponibilidade, não empate."""
    soma = sum(valores.values())
    if soma <= 0:
        raise ModeloError(
            f"soma não positiva ({soma}) — série indisponível, não empate. "
            "Dividir por zero disfarçado de empate produziria número inventado."
        )
    return {k: v / soma for k, v in valores.items()}


@dataclass(frozen=True)
class Sinal:
    """Uma família de evidência, com seu peso e sua honestidade declarada."""

    nome: str
    #: Composição observada — soma qualquer, é normalizada internamente.
    valores: dict[str, float]
    #: Quanto esta família concentra em relação ao voto. 1,0 = já na escala do
    #: voto. Acima de 1 significa "o sinal é mais achatado que o voto".
    inclinacao: float = 1.0
    #: Peso na combinação. Zero desliga a família sem removê-la do registro.
    peso: float = 1.0
    #: Quando a inclinação foi estimada, e contra o quê.
    calibrado_em: date | None = None
    calibrado_contra: str = ""
    #: Limitação conhecida. Entra no relatório, não fica só no comentário.
    vies_declarado: str = ""

    def __post_init__(self) -> None:
        if self.peso < 0:
            raise ModeloError(f"peso negativo em {self.nome!r}: {self.peso}")
        if not math.isfinite(self.inclinacao) or self.inclinacao <= 0:
            raise ModeloError(f"inclinação inválida em {self.nome!r}: {self.inclinacao}")
        if not self.valores:
            raise ModeloError(f"sinal {self.nome!r} sem valores")

    def coordenadas(self, candidatos: tuple[str, ...]) -> dict[str, float]:
        """Coordenadas log-razão já com a inclinação aplicada."""
        faltando = set(candidatos) - set(self.valores)
        if faltando:
            raise ModeloError(
                f"sinal {self.nome!r} não cobre {sorted(faltando)} — ausência não "
                "vira zero, porque zero afirmaria que o candidato não tem nada"
            )
        recorte = normalizar({c: self.valores[c] for c in candidatos})
        return {c: self.inclinacao * v for c, v in clr(recorte).items()}


@dataclass
class Modelo:
    """Combinação de famílias de sinal em fatia de voto estimada."""

    candidatos: tuple[str, ...]
    sinais: list[Sinal] = field(default_factory=list)
    #: Depois de quantos dias uma calibração é considerada vencida.
    validade_dias: int = 120

    def __post_init__(self) -> None:
        if len(self.candidatos) < 2:
            raise ModeloError("é preciso pelo menos dois candidatos para haver disputa")
        if len(set(self.candidatos)) != len(self.candidatos):
            raise ModeloError("candidato repetido na lista")

    def fatias(self) -> dict[str, float]:
        """Fatia de voto estimada por candidato. Soma 1.

        Média **ponderada simples** no espaço log-razão. É deliberadamente o
        método mais simples que respeita a geometria do problema: a literatura
        de combinação de previsões mostra que, com poucos dados, a média simples
        é difícil de bater, e as M-Competitions confirmam que sofisticação só
        compensa em escala que não temos.
        """
        if not self.sinais:
            raise ModeloError("nenhum sinal — o modelo não inventa distribuição")
        ativos = [s for s in self.sinais if s.peso > 0]
        if not ativos:
            raise ModeloError("todos os sinais estão com peso zero")
        total = sum(s.peso for s in ativos)
        combinado = {c: 0.0 for c in self.candidatos}
        for sinal in ativos:
            coords = sinal.coordenadas(self.candidatos)
            for c in self.candidatos:
                combinado[c] += sinal.peso * coords[c] / total
        return de_clr(combinado)

    def probabilidade_de_segundo_turno(self) -> float:
        """Probabilidade de haver 2º turno, pelo art. 77 §3º da Constituição.

        Eleito no primeiro turno quem obtém MAIS da metade dos votos válidos.
        Aqui isto é uma leitura determinística da estimativa central, e por isso
        vem acompanhada de :meth:`avisos` — uma fatia estimada em 50,4% não
        carrega a confiança que o número sugere.
        """
        maior = max(self.fatias().values())
        return 0.0 if maior > 0.5 else 1.0

    def ordem(self) -> list[tuple[str, float]]:
        """Candidatos do maior para o menor. É a saída em que confiamos mais.

        O backtest de 2022 mostrou o sinal de atenção **bom para ordenar e ruim
        para dimensionar**: acertou os dois do 2º turno na ordem certa, errando
        12,6 pp na magnitude antes da transformação. Ordenar é a pergunta que o
        dado responde bem.
        """
        return sorted(self.fatias().items(), key=lambda kv: -kv[1])

    def avisos(self, hoje: date | None = None) -> list[str]:
        """O que está vencido, ausente ou enviesado. Vazio é bom sinal.

        Existe para que o modelo nunca devolva um número limpo escondendo que a
        calibração é de outra eleição. Quem consome decide o que fazer; o que o
        modelo não faz é ficar quieto.
        """
        agora = hoje or date.today()
        fora: list[str] = []
        for sinal in self.sinais:
            if sinal.peso <= 0:
                fora.append(f"{sinal.nome}: desligado (peso zero)")
                continue
            if sinal.calibrado_em is None:
                fora.append(f"{sinal.nome}: nunca calibrado contra resultado real")
            else:
                idade = (agora - sinal.calibrado_em).days
                if idade > self.validade_dias:
                    fora.append(
                        f"{sinal.nome}: calibrado há {idade} dias contra "
                        f"{sinal.calibrado_contra or 'origem não declarada'} — "
                        f"vencido (validade {self.validade_dias} dias)"
                    )
            if sinal.vies_declarado:
                fora.append(f"{sinal.nome}: {sinal.vies_declarado}")
        if len(self.sinais) < 2:
            fora.append(
                "apenas uma família de sinal — o backtest de 2022 mostrou que "
                "atenção sozinha erra por não enxergar estrutura partidária "
                "(Ciro Gomes +8,36 pp, Simone Tebet -3,31 pp)"
            )
        return fora


def brier(previsto: dict[str, float], ocorrido: dict[str, bool]) -> float:
    """Brier score multi-categoria. Acaso puro entre dois lados = 0,25.

    É a régua do produto. Um modelo que empurra probabilidade para 50% "para não
    errar feio" não reduz erro — transfere erro para cá, e um número amortecido
    de propósito num histórico auditável é o único defeito que não tem conserto.
    """
    faltando = set(previsto) - set(ocorrido)
    if faltando:
        raise ModeloError(f"sem desfecho declarado para {sorted(faltando)}")
    return sum((p - (1.0 if ocorrido[c] else 0.0)) ** 2 for c, p in previsto.items()) / len(previsto)


def erro_absoluto_medio(previsto: dict[str, float], real: dict[str, float]) -> float:
    """Erro médio em pontos percentuais. A métrica do backtest."""
    comuns = set(previsto) & set(real)
    if not comuns:
        raise ModeloError("nenhum candidato em comum entre previsto e real")
    return sum(abs(previsto[c] - real[c]) * 100 for c in comuns) / len(comuns)
