# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Matemática composicional compartilhada: log-razão centrada (CLR) e a volta.

Extraído em 30/08/2026 depois que uma varredura estrutural achou a mesma
fórmula duplicada em dois módulos — ``modelo_eleitoral.clr``/``de_clr`` e
``atencao_wikimedia.log_razao``/``de_log_razao`` — com uma divergência real
entre as cópias: uma validava composição negativa, a outra não. Duas cópias da
mesma matemática são duas chances de divergir, e já tinham divergido.

Fatia de voto (ou de atenção) é dado composicional: soma 1, vive num simplex,
onde média e regressão comuns não valem. A transformação log-razão centrada
(Aitchison; Stoetzer et al., *Political Analysis* 2019) leva a composição para
um espaço onde somar faz sentido:

    clr(x)_i = ln(x_i) - (1/n) * sum_j ln(x_j)

``de_clr`` subtrai o máximo antes de exponenciar — proteção escrita depois do
incidente real do beta 8,5, quando uma inclinação alta sobre coordenada grande
produziu ``exp(40)`` e uma composição degenerada sem lançar exceção nenhuma.
Composição quase degenerada continua sendo a entrada que mais quebra esta
conta; é por isso que a proteção mora AQUI, uma vez, em vez de em cada cópia.

O PARÂMETRO ``erro``, o que faz este módulo ser reutilizável sem forçar um tipo
de exceção único: cada módulo que chama isto tem seu próprio vocabulário de
falha (``ModeloError`` no backtest eleitoral, ``AtencaoError`` no sinal de
atenção) e continua levantando o que sempre levantou — só a fórmula é
compartilhada, não o contrato de erro. Sem isso, unificar teria forçado uma
mudança de tipo de exceção em código já testado, ou uma cadeia de herança que
quebraria ``pytest.raises`` na direção errada.
"""

from __future__ import annotations

import math

DEFAULT_PISO = 1e-6


class ComposicionalError(RuntimeError):
    """Falha genérica de operação composicional, quando quem chama não injeta o próprio erro."""


def normalizar(
    valores: dict[str, float], *, erro: type[Exception] = ComposicionalError
) -> dict[str, float]:
    """Fatias que somam 1. Soma zero é indisponibilidade, não empate."""
    soma = sum(valores.values())
    if soma <= 0:
        raise erro(
            f"soma não positiva ({soma}) — série indisponível, não empate. "
            "Dividir por zero disfarçado de empate produziria número inventado."
        )
    return {k: v / soma for k, v in valores.items()}


def clr(
    composicao: dict[str, float],
    *,
    piso: float = DEFAULT_PISO,
    erro: type[Exception] = ComposicionalError,
) -> dict[str, float]:
    """Log-razão centrada: leva uma composição para o espaço onde se soma.

    ``piso`` evita ``log(0)``. Fatia zerada é ausência de sinal, não
    impossibilidade — tratá-la como impossibilidade eliminaria candidato do
    páreo por falta de dado, que é o oposto de medir.

    Recusa composição com valor negativo. Uma das duas cópias que existiam
    antes da unificação não recusava — divergência real que este módulo
    fecha para as duas.
    """
    if not composicao:
        raise erro("composição vazia")
    if any(v < 0 for v in composicao.values()):
        raise erro(f"composição com valor negativo: {composicao}")
    seguras = {k: max(v, piso) for k, v in composicao.items()}
    media_log = sum(math.log(v) for v in seguras.values()) / len(seguras)
    return {k: math.log(v) - media_log for k, v in seguras.items()}


def de_clr(
    coordenadas: dict[str, float], *, erro: type[Exception] = ComposicionalError
) -> dict[str, float]:
    """Volta do espaço log-razão para uma composição que soma 1.

    Subtrai o máximo antes de exponenciar. Sem isso, coordenada grande demais
    faz ``math.exp`` estourar em ``OverflowError`` cru, ou produz composição
    degenerada em silêncio — foi exatamente o defeito do beta 8,5, aplicado a
    um candidato com atenção muito acima da faixa calibrada.
    """
    if not coordenadas:
        raise erro("coordenadas vazias")
    teto = max(coordenadas.values())
    expo = {k: math.exp(v - teto) for k, v in coordenadas.items()}
    soma = sum(expo.values())
    if soma <= 0 or not math.isfinite(soma):
        raise erro("composição degenerada ao voltar do log-razão")
    return {k: v / soma for k, v in expo.items()}
