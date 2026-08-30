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

from asus_theye.markets.composicional import clr as _clr, de_clr as _de_clr, normalizar as _normalizar
from dataclasses import dataclass, field
from datetime import date


class ModeloError(RuntimeError):
    """O modelo recusa produzir número. Nunca devolve palpite silencioso."""


#: A matemática de log-razão vive em ``composicional.py`` desde 30/08/2026,
#: quando uma varredura estrutural achou a mesma fórmula duplicada aqui e em
#: ``atencao_wikimedia.py`` — com uma divergência real (uma cópia validava
#: composição negativa, a outra não). Este módulo continua expondo os mesmos
#: nomes e continua levantando ``ModeloError`` (nunca o genérico
#: ``ComposicionalError``), via o parâmetro ``erro`` injetado — nenhum código
#: que já chamava ``clr``/``de_clr``/``normalizar`` daqui precisa mudar.
def clr(composicao: dict[str, float], *, piso: float = 1e-6) -> dict[str, float]:
    """Log-razão centrada: leva uma composição para o espaço onde se soma."""
    return _clr(composicao, piso=piso, erro=ModeloError)


def de_clr(coordenadas: dict[str, float]) -> dict[str, float]:
    """Volta do espaço log-razão para uma composição que soma 1."""
    return _de_clr(coordenadas, erro=ModeloError)


def normalizar(valores: dict[str, float]) -> dict[str, float]:
    """Fatias que somam 1. Soma zero é indisponibilidade, não empate."""
    return _normalizar(valores, erro=ModeloError)


@dataclass(frozen=True)
class Sinal:
    """Uma família de evidência, com seu peso e sua honestidade declarada."""

    nome: str
    #: Composição observada — soma qualquer, é normalizada internamente.
    valores: dict[str, float]
    #: Quanto esta família concentra em relação ao voto. 1,0 = já na escala do
    #: voto, e é o ÚNICO valor honesto enquanto não houver calibração do ciclo
    #: corrente. Acima de 1 significa "o sinal é mais achatado que o voto".
    inclinacao: float = 1.0
    #: Ciclo eleitoral em que a inclinação foi medida (ex.: "ele2022").
    #: Inclinação de um ciclo NÃO vale no seguinte — ordem do titular, e ele
    #: está certo: em 2026 Bolsonaro não concorre, entraram dois candidatos
    #: nativos digitais e duas famílias de sinal deixaram de existir. Um beta de
    #: 8,5 medido em 2022 aplicado a 2026 deu 97,8% a um candidato com 1,4% do
    #: tempo de TV — sem erro nenhum, e absurdo.
    ciclo_de_calibracao: str = ""
    #: Peso na combinação. Zero desliga a família sem removê-la do registro.
    peso: float = 1.0
    #: Quando a inclinação foi estimada, e contra o quê.
    calibrado_em: date | None = None
    calibrado_contra: str = ""
    #: Limitação conhecida. Entra no relatório, não fica só no comentário.
    vies_declarado: str = ""
    #: Maior fatia observada no conjunto onde a inclinação foi calibrada.
    #: Fora dessa faixa, aplicar a inclinação é EXTRAPOLAR — e extrapolação com
    #: inclinação alta explode. Em 2022 o líder de atenção tinha 0,24 do
    #: excedente; aplicar o mesmo beta a alguém com 0,51 produziu 97,8% para um
    #: candidato com 1,4% do tempo de TV. O número saiu sem erro nenhum, e era
    #: absurdo. ``None`` desliga a checagem, e quem desliga assume o risco.
    faixa_calibrada_ate: float | None = None

    def __post_init__(self) -> None:
        if self.peso < 0:
            raise ModeloError(f"peso negativo em {self.nome!r}: {self.peso}")
        if not math.isfinite(self.inclinacao) or self.inclinacao <= 0:
            raise ModeloError(f"inclinação inválida em {self.nome!r}: {self.inclinacao}")
        if not self.valores:
            raise ModeloError(f"sinal {self.nome!r} sem valores")

    def fora_da_faixa(self, candidatos: tuple[str, ...]) -> float | None:
        """Quanto a maior fatia excede a faixa onde a inclinação foi calibrada.

        ``None`` quando está dentro, ou quando não há faixa declarada.
        """
        if self.faixa_calibrada_ate is None:
            return None
        recorte = normalizar({c: self.valores[c] for c in candidatos if c in self.valores})
        maior = max(recorte.values(), default=0.0)
        return maior - self.faixa_calibrada_ate if maior > self.faixa_calibrada_ate else None

    def inclinacao_valida(self, ciclo_alvo: str) -> float:
        """A inclinação que pode ser aplicada, dado o ciclo que se quer prever.

        Devolve 1,0 — isto é, NENHUMA amplificação — quando a inclinação foi
        medida noutro ciclo. Não é conservadorismo: é que o número medido em
        2022 descreve um campo eleitoral que não existe mais, e usá-lo seria
        inventar precisão a partir de um mundo extinto.
        """
        if not ciclo_alvo or not self.ciclo_de_calibracao:
            return self.inclinacao
        return self.inclinacao if self.ciclo_de_calibracao == ciclo_alvo else 1.0

    def coordenadas(
        self, candidatos: tuple[str, ...], *, ciclo_alvo: str = ""
    ) -> dict[str, float]:
        """Coordenadas log-razão com a inclinação VÁLIDA para o ciclo alvo."""
        faltando = set(candidatos) - set(self.valores)
        if faltando:
            raise ModeloError(
                f"sinal {self.nome!r} não cobre {sorted(faltando)} — ausência não "
                "vira zero, porque zero afirmaria que o candidato não tem nada"
            )
        recorte = normalizar({c: self.valores[c] for c in candidatos})
        beta = self.inclinacao_valida(ciclo_alvo)
        return {c: beta * v for c, v in clr(recorte).items()}


@dataclass
class Modelo:
    """Combinação de famílias de sinal em fatia de voto estimada."""

    candidatos: tuple[str, ...]
    sinais: list[Sinal] = field(default_factory=list)
    #: Depois de quantos dias uma calibração é considerada vencida.
    validade_dias: int = 120
    #: Põe as famílias em escala comparável antes de ponderar. Desligar faz
    #: `peso` deixar de significar peso — ver o comentário em `fatias`.
    normalizar_escala: bool = True
    #: Ciclo que este modelo está prevendo. Sinal com inclinação calibrada em
    #: outro ciclo tem a inclinação NEUTRALIZADA para 1,0, com aviso — nunca
    #: aplicada em silêncio.
    ciclo: str = ""

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
            coords = sinal.coordenadas(self.candidatos, ciclo_alvo=self.ciclo)
            if self.normalizar_escala:
                # Sem isto, `peso` NÃO significa peso. Inclinação e peso se
                # multiplicam no espaço log-razão: um sinal com inclinação 8,5
                # produz coordenadas oito vezes maiores que um com 1,0, e domina
                # a média mesmo com pesos iguais. Foi o que fez um candidato com
                # 1,4% do tempo de TV sair com 97,8% de chance.
                #
                # Dividir pelo desvio das próprias coordenadas põe as famílias em
                # escala comparável; a inclinação continua ditando a FORMA da
                # distribuição, e o peso volta a ditar a influência.
                escala = (sum(v * v for v in coords.values()) / len(coords)) ** 0.5
                if escala > 1e-9:
                    coords = {c: v / escala for c, v in coords.items()}
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
            if (self.ciclo and sinal.ciclo_de_calibracao
                    and sinal.ciclo_de_calibracao != self.ciclo
                    and sinal.inclinacao != 1.0):
                fora.append(
                    f"{sinal.nome}: inclinação {sinal.inclinacao:.1f} foi medida em "
                    f"{sinal.ciclo_de_calibracao} e NÃO se aplica a {self.ciclo} — "
                    "neutralizada para 1,0. O campo eleitoral mudou; o parâmetro "
                    "descreve um mundo que não existe mais."
                )
            excesso = sinal.fora_da_faixa(self.candidatos)
            if excesso is not None:
                fora.append(
                    f"{sinal.nome}: EXTRAPOLAÇÃO — a maior fatia excede em "
                    f"{excesso:.1%} a faixa onde a inclinação foi calibrada "
                    f"(até {sinal.faixa_calibrada_ate:.0%}). Fora dessa faixa a "
                    "inclinação amplifica sem base medida."
                )
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
    """Erro médio em pontos percentuais. A métrica do backtest.

    As duas entradas são FRAÇÃO (0–1), nunca percentual (0–100) — mesma escala
    que o resto deste módulo usa em toda parte. É o ponto exato da mina que a
    varredura estrutural de 30/08/2026 apontou: ``fonte_tse.py`` publica
    ``pvap`` em 0–100 (é o formato nativo do TSE, ex.: 48.43), e alimentar
    ``real`` direto de lá — sem converter — faria esta função multiplicar por
    100 de novo e devolver um "erro" absurdo (~4794 em vez de ~0,35), SEM
    lançar exceção nenhuma. A guarda abaixo torna esse erro de escala barulhento
    em vez de silencioso. Use
    :func:`asus_theye.markets.fonte_tse.fracao_do_percentual_tse` para
    converter antes de chamar esta função com dado do TSE.
    """
    comuns = set(previsto) & set(real)
    if not comuns:
        raise ModeloError("nenhum candidato em comum entre previsto e real")
    fora_de_faixa = {
        c: (previsto.get(c), real.get(c))
        for c in comuns
        if not (0.0 <= previsto[c] <= 1.0 and 0.0 <= real[c] <= 1.0)
    }
    if fora_de_faixa:
        amostra = dict(list(fora_de_faixa.items())[:3])
        raise ModeloError(
            f"valor fora de [0,1]: {amostra} — isto é fração, não percentual. "
            "Se o dado vem do TSE (pvap é 0–100), converta com "
            "fonte_tse.fracao_do_percentual_tse() antes de chamar."
        )
    return sum(abs(previsto[c] - real[c]) * 100 for c in comuns) / len(comuns)
