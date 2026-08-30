# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inferência conformal adaptativa: a faixa se corrige sozinha quando o mundo muda.

É a implementação literal da regra permanente do titular:

    "O mundo muda, os algoritmos mudam. O motor tem que ser dinâmico, tem que se
    renovar, tem que estar sempre pesquisando novidades."

O conformal comum (ver ``conformal.py``) garante cobertura **desde que** o caso
novo seja intercambiável com os de calibração. Essa hipótese é forte e, no nosso
caso, quase certamente falsa: os candidatos de 2026 não são intercambiáveis com
os de 2022 — Bolsonaro não concorre, entraram dois nativos digitais, X fechou o
acesso gratuito e o Reddit passou a exigir OAuth. Sob hipótese violada, a
cobertura anunciada vira ficção.

A INFERÊNCIA ADAPTATIVA resolve isso trocando a hipótese por um mecanismo. Em vez
de fixar ``alpha``, ela o ajusta a cada resultado observado:

    alpha_{t+1} = alpha_t + gamma * (alpha_alvo - erro_t)

onde ``erro_t`` vale 1 se o valor real caiu **fora** da faixa e 0 se caiu dentro.
A leitura é direta: errou, aperta; acertou, afrouxa um pouco. Gibbs & Candès
(Stanford, arXiv:2106.00170) provam que isso mantém a cobertura de **longo
prazo** perto do alvo mesmo sob mudança de distribuição — sem exigir
permutabilidade, sem exigir estacionariedade, e sem supor forma de distribuição.

────────────────────────────────────────────────────────────────────────────
A TROCA QUE ISSO REPRESENTA, dita sem eufemismo

O conformal comum promete cobertura **em cada** previsão, sob hipótese que não
vale. O adaptativo promete cobertura **na média ao longo do tempo**, sem hipótese
nenhuma. É uma garantia mais fraca por previsão e muito mais robusta na prática —
e, para quem vai operar durante um ciclo eleitoral inteiro sob mudança contínua,
é a troca certa.

O que ele **não** faz: consertar uma previsão individual. Se o modelo estiver
errado sobre um candidato, a faixa dele fica larga, não certa. Adaptação corrige
calibração, nunca acurácia.
────────────────────────────────────────────────────────────────────────────

POR QUE ISTO É O ALARME DE OBSOLESCÊNCIA. O ``alpha`` corrente é um termômetro
legível: se ele desabou muito abaixo do alvo, o modelo está errando mais do que
deveria e a faixa está sendo forçada a alargar para compensar. Isso é
exatamente "a calibração venceu", medido em vez de suposto —
:meth:`Adaptador.diagnostico` traduz isso em texto.

Os testes clássicos de quebra estrutural (Chow, Bai-Perron) fariam esse trabalho
com mais rigor, e são **inaplicáveis** aqui: exigem dezenas a centenas de
observações, e temos uma ou duas eleições. O caminho formal para amostra
minúscula são os *e-values* de inferência sempre-válida (Ramdas e grupo, CMU,
arXiv:2203.03532), ainda não implementados aqui — fica registrado como o próximo
passo, e não como algo que este arquivo já faz.

ESCOLHA DE ``gamma``. É o tamanho do passo: quanto o ``alpha`` anda a cada erro.
Alto demais, a faixa oscila e vira sanfona; baixo demais, leva ciclos para
reagir e a adaptação não serve para nada. Gibbs & Candès usam 0,005 a 0,05 em
séries longas; aqui o padrão é **0,05**, o mais reativo da faixa, porque
observamos poucos eventos e não temos o luxo de reagir devagar.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field

from asus_theye.markets.conformal import ConformalError


@dataclass
class Adaptador:
    """Mantém a cobertura no alvo ajustando ``alpha`` a cada resultado."""

    #: Cobertura desejada no longo prazo (0,10 = 90%).
    alpha_alvo: float = 0.10
    #: Tamanho do passo. Ver a nota sobre gamma no cabeçalho do módulo.
    gamma: float = 0.05
    #: Estado corrente. Começa igual ao alvo e caminha a partir dele.
    alpha_corrente: float = field(default=None)  # type: ignore[assignment]
    #: Histórico de acertos da FAIXA (True = o real caiu dentro).
    historico: list[bool] = field(default_factory=list)
    #: Trilha do alpha ao longo do tempo, para auditoria.
    trilha_alpha: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 < self.alpha_alvo < 1:
            raise ConformalError(f"alpha_alvo fora de (0,1): {self.alpha_alvo}")
        if not 0 < self.gamma <= 1:
            raise ConformalError(f"gamma fora de (0,1]: {self.gamma}")
        if self.alpha_corrente is None:
            self.alpha_corrente = self.alpha_alvo
        self.trilha_alpha.append(self.alpha_corrente)

    def observar(self, caiu_dentro: bool) -> float:
        """Registra um resultado e devolve o ``alpha`` para a próxima previsão.

        A atualização é ``alpha += gamma * (alvo - erro)``. Quando a faixa erra,
        ``erro = 1`` e o alpha **diminui**, o que alarga a próxima faixa. Quando
        acerta, o alpha sobe um pouco e a faixa aperta. É um controlador de
        realimentação, e a intuição é a de um termostato.
        """
        erro = 0.0 if caiu_dentro else 1.0
        self.historico.append(caiu_dentro)
        novo = self.alpha_corrente + self.gamma * (self.alpha_alvo - erro)
        # Prende dentro de (0,1): alpha fora disso não tem significado, e um
        # alpha negativo produziria faixa infinita sem lançar erro nenhum.
        self.alpha_corrente = min(max(novo, 1e-4), 1 - 1e-4)
        self.trilha_alpha.append(self.alpha_corrente)
        return self.alpha_corrente

    @property
    def cobertura_observada(self) -> float | None:
        """Fração de acertos da faixa até aqui. ``None`` antes do 1º resultado."""
        if not self.historico:
            return None
        return sum(self.historico) / len(self.historico)

    def diagnostico(self) -> str:
        """Tradução do estado em frase. É o alarme de calibração vencida.

        Existe porque um número solto (``alpha = 0,013``) não diz a ninguém que o
        modelo está em apuros. A frase diz.
        """
        if not self.historico:
            return "sem resultado observado ainda — nada a diagnosticar"
        obs = self.cobertura_observada
        assert obs is not None
        alvo = 1 - self.alpha_alvo
        partes = [
            f"cobertura observada {obs*100:.1f}% (alvo {alvo*100:.0f}%) "
            f"em {len(self.historico)} resultado(s)",
            f"alpha corrente {self.alpha_corrente:.4f} (partiu de {self.alpha_alvo:.4f})",
        ]
        # O alpha desabar é o sintoma de que o modelo passou a errar demais e a
        # adaptação está compensando alargando a faixa.
        if self.alpha_corrente < self.alpha_alvo / 3:
            partes.append(
                "ALERTA: o alpha desabou — o modelo vem errando muito mais que o "
                "previsto e a faixa está sendo forçada a alargar para compensar. "
                "Isso é calibração vencida medida, não suposta: reestime os "
                "parâmetros contra resultado recente antes de confiar na saída."
            )
        elif self.alpha_corrente > min(0.9, self.alpha_alvo * 3):
            partes.append(
                "aviso: o alpha subiu muito — as faixas podem estar largas demais "
                "e o modelo, conservador em excesso. Faixa que sempre acerta por "
                "ser larga não informa nada."
            )
        if len(self.historico) < 5:
            partes.append(
                f"histórico curto ({len(self.historico)}): a cobertura observada "
                "ainda não é estimativa confiável de nada"
            )
        return " | ".join(partes)

    def estavel(self, *, tolerancia: float = 0.10, minimo: int = 10) -> bool:
        """A cobertura observada está perto do alvo, com histórico suficiente?

        É a condição para confiar na faixa. Antes disso o adaptador ainda está
        aprendendo, e dizer o contrário seria vender aprendizado como garantia.
        """
        obs = self.cobertura_observada
        if obs is None or len(self.historico) < minimo:
            return False
        return abs(obs - (1 - self.alpha_alvo)) <= tolerancia


def simular_deriva(
    residuos_iniciais: list[float],
    residuos_depois: list[float],
    *,
    alpha_alvo: float = 0.10,
    gamma: float = 0.05,
) -> tuple[Adaptador, dict[str, float]]:
    """Mostra o adaptador reagindo a uma mudança de regime.

    Serve para responder, com número, à pergunta que o titular fez de outro
    jeito: *o motor percebe que o mundo mudou?* Alimenta o adaptador com
    resíduos de um regime e depois de outro, e devolve a cobertura em cada fase.

    Não é teste de unidade — é demonstração reproduzível do comportamento.
    """
    if not residuos_iniciais or not residuos_depois:
        raise ConformalError("ambas as fases precisam de resíduos")
    a = Adaptador(alpha_alvo=alpha_alvo, gamma=gamma)
    limite = statistics.quantiles(residuos_iniciais, n=100)[int((1 - alpha_alvo) * 100) - 1] \
        if len(residuos_iniciais) >= 2 else max(residuos_iniciais)

    def rodar(residuos: list[float]) -> float:
        acertos = 0
        for r in residuos:
            # A faixa cresce quando alpha cai: fator simples e monotônico.
            largura = limite * (alpha_alvo / max(a.alpha_corrente, 1e-4))
            dentro = r <= largura
            acertos += dentro
            a.observar(dentro)
        return acertos / len(residuos)

    antes = rodar(residuos_iniciais)
    marca = len(a.historico)
    depois = rodar(residuos_depois)
    return a, {
        "cobertura_fase_1": antes,
        "cobertura_fase_2": depois,
        "alpha_na_virada": a.trilha_alpha[marca],
        "alpha_final": a.alpha_corrente,
    }
