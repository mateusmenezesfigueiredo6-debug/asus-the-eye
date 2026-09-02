# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Atlas de Algoritmos v0 — o catálogo interno de algoritmos absorvidos.

A pergunta do titular (01/09/2026): existe uma central que reúna algoritmos
preditivos, de graça? Existe — Hugging Face, OpenML, Monash, e bibliotecas que
são centrais em si (Nixtla, sktime, Darts, GluonTS). A decisão da casa não é
construir outra central: é construir a NOSSA CAMADA sobre elas. Este módulo é
essa camada, na v0 mínima e deliberada:

  * CATÁLOGO com proveniência: cada algoritmo absorvido entra com hub de
    origem, licença e versão — nada anônimo, nada clonado, adaptador fino
    sobre a biblioteca instalada (a implementação continua sendo da Nixtla,
    com a licença dela; NOSSA é a medição).
  * BENCHMARK NOSSO, nos NOSSOS folds: os mesmos 18+ meses walk-forward que
    medem o nowcast (janela de 120 meses, mesmo alvo SGS 433, mesmo limiar do
    fold), com a MESMA regra dura do baseline Focus (previsão > limiar → 1,0)
    — três números comparáveis entre si e com os já selados: ridge 0,0575 e
    Focus 0,2222 em 01/09/2026.
  * Resultado REGISTRADO no mlops (modelo/versão/corrida) e SELADO na
    corrente — benchmark que não sela é opinião.

Escopo v0 contido de propósito (decisão do plano de 01/09/2026): só as
baselines clássicas da statsforecast. Modelos-fundação (Chronos, TimesFM, t0)
ficam para a v1, quando houver liquidações suficientes para pontuá-los em
produção, não só em backtest.

A importação da statsforecast é PREGUIÇOSA: o motor inteiro não passa a
depender do numba por causa do Atlas; quem não instalou o extra recebe
``AtlasError`` com a instrução de instalação, nunca ImportError solto.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from asus_theye.markets.fonte_base import FonteError


class AtlasError(RuntimeError):
    """Algoritmo fora do catálogo, dependência ausente ou série insuficiente."""


#: O catálogo. Acrescentar algoritmo = acrescentar entrada AQUI, com hub,
#: licença e versão absorvida — a mesma disciplina do contrato do store:
#: nada entra sem declarar.
CATALOGO: dict[str, dict[str, str]] = {
    "auto_arima": {
        "nome": "AutoARIMA (Hyndman-Khandakar)",
        "hub": "Nixtla statsforecast (PyPI/GitHub)",
        "licenca": "Apache-2.0",
        "versao_absorvida": "2.1.1",
    },
    "auto_ets": {
        "nome": "AutoETS (espaço de estados exponencial)",
        "hub": "Nixtla statsforecast (PyPI/GitHub)",
        "licenca": "Apache-2.0",
        "versao_absorvida": "2.1.1",
    },
    "auto_theta": {
        "nome": "AutoTheta (Assimakopoulos & Nikolopoulos)",
        "hub": "Nixtla statsforecast (PyPI/GitHub)",
        "licenca": "Apache-2.0",
        "versao_absorvida": "2.1.1",
    },
}

MINIMO_DE_PONTOS = 24


def _modelo(algoritmo: str) -> Any:
    if algoritmo not in CATALOGO:
        raise AtlasError(f"algoritmo {algoritmo!r} fora do catálogo: {sorted(CATALOGO)}")
    try:
        from statsforecast.models import AutoARIMA, AutoETS, AutoTheta
    except ImportError as exc:  # numba/statsforecast não instalados
        raise AtlasError(
            "statsforecast ausente — instale o extra do Atlas: .venv/bin/pip install statsforecast"
        ) from exc
    return {"auto_arima": AutoARIMA, "auto_ets": AutoETS, "auto_theta": AutoTheta}[algoritmo]()


def prever_um_passo(valores: Sequence[float], algoritmo: str) -> float:
    """Previsão h=1 do algoritmo do catálogo sobre a série dada.

    Adaptador fino: ajusta no histórico completo recebido e devolve UM passo à
    frente. Série curta demais levanta — palpite sobre meia dúzia de pontos
    não é previsão, é ruído com assinatura.
    """
    serie = np.asarray(list(valores), dtype=float)
    if serie.size < MINIMO_DE_PONTOS:
        raise AtlasError(
            f"série com {serie.size} pontos; o mínimo honesto é {MINIMO_DE_PONTOS}"
        )
    if not np.isfinite(serie).all():
        raise AtlasError("série com NaN/inf — dado podre não entra em modelo")
    modelo = _modelo(algoritmo)
    ajustado = modelo.fit(serie)
    previsao = ajustado.predict(h=1)["mean"]
    return float(np.asarray(previsao).ravel()[0])


def benchmark_nos_folds_do_ipca(
    *,
    algoritmos: Sequence[str] | None = None,
    janela: int = 120,
    transport: Any = None,
) -> dict[str, Any]:
    """Brier de cada baseline do catálogo nos MESMOS meses do walk-forward.

    Régua idêntica ao baseline Focus (§4.3 do spec do nowcast): a previsão de
    ponto vira decisão dura contra o limiar DO PRÓPRIO fold; o desfecho já foi
    apurado contra a série oficial. Comparável, portanto, aos números selados
    do ridge e do Focus — e carrega a mesma ressalva de dureza.
    """
    from asus_theye.markets.nowcast import montar_painel, walk_forward

    escolhidos = list(algoritmos) if algoritmos else sorted(CATALOGO)
    painel = montar_painel(transport=transport)
    folds = [f for f in walk_forward(painel, "R2") if f.probabilidade is not None]
    if not folds:
        raise AtlasError("nenhum fold avaliável — sem meses walk-forward não há benchmark")

    indice_do_mes = {mes: i for i, mes in enumerate(painel.meses)}
    resultados: dict[str, Any] = {}
    for algoritmo in escolhidos:
        pares: list[tuple[float, int]] = []
        for fold in folds:
            fim = indice_do_mes[fold.mes]  # exclusivo: o mês avaliado fica FORA
            historico = painel.alvo[max(0, fim - janela) : fim]
            previsto = prever_um_passo(historico, algoritmo)
            p_dura = 1.0 if previsto > float(fold.limiar) else 0.0
            pares.append((p_dura, int(fold.desfecho)))
        brier = sum((p - o) ** 2 for p, o in pares) / len(pares)
        resultados[algoritmo] = {
            "brier": round(brier, 6),
            "n_meses": len(pares),
            "regra": "dura (previsão > limiar do fold), a mesma do baseline Focus",
            **CATALOGO[algoritmo],
        }
    return {
        "meses_avaliados": [f.mes for f in folds],
        "janela_meses": janela,
        "algoritmos": resultados,
    }
