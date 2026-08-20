# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comparação contra o consenso Focus — a linha de base, medida com honestidade.

Pareia o consenso que **existia antes** do fato (vintage arquivado) com o valor
que a fonte oficial acabou publicando, e mede o erro. É a referência sem a qual
nenhuma afirmação de calibração significa coisa alguma: dizer "acertamos" sem
dizer "comparado a quê" não é medição, é propaganda.

**A ressalva que governa este módulo.** O gerador WPAM usa o Focus como sinal
dominante (peso 20, contra 10 do IPCA-15): nossa probabilidade **deriva** do
consenso. Logo é impossível afirmar que superamos o consenso — medir "nosso p
contra o Focus" mediria sobretudo o nosso esquema de pesos aplicado ao insumo
dele. Todo resultado daqui carrega essa dependência declarada, e o que se mede
é o que é honesto medir: **o erro do próprio Focus**, que é a linha de base, e
o **efeito de acrescentar o IPCA-15**, que é a contribuição própria.

**Vintage, nunca revisado.** O consenso de hoje só existe hoje; o boletim é
revisado depois. Parear com o valor revisado daria vantagem informacional
artificial — por isso a fonte é `vintage_focus.jsonl`, arquivado no momento em
que o consenso valia, com hash.

Conceito lido em publicação de terceiro e reimplementado de forma independente;
registro em ``reports/provenance/Kalshi-consensus-benchmark.md``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# De qual ÁREA cada indicador do Focus fala. Sem isto o pareamento por mês
# casaria a mediana do IPCA com o valor observado do câmbio — números da mesma
# data que não respondem à mesma pergunta. O erro resultante seria fabricado, e
# ele seria SELADO na corrente e ancorado on-chain: exatamente a falha que esta
# plataforma existe para impedir.
AREA_DO_INDICADOR = {"IPCA": "macroeconomia", "Selic": "juros", "Câmbio": "cambio"}

VINTAGE_PADRAO = Path("reports/markets/vintage_focus.jsonl")
RESOLUCOES_PADRAO = Path("reports/markets/resolucoes.jsonl")

# Abaixo disto, nenhuma estatística agregada é emitida. Não é excesso de zelo:
# com um punhado de meses, MAE e taxa de acerto oscilam tanto que o número diz
# mais sobre o acaso do que sobre o previsor — e um número publicado é lido como
# se valesse. Recusar é a resposta correta, e ela vem dita.
AMOSTRA_MINIMA = 12

# Regimes de surpresa, em pontos percentuais de erro do consenso. Os cortes são
# PROVISÓRIOS e estão declarados como tal: separar mês tranquilo de mês de
# choque exige calibrar na variância do IPCA, e ainda não há amostra para isso.
# Importar o corte de outra economia seria trazer junto a variância dela.
CHOQUE_MODERADO = 0.1
CHOQUE_MAIOR = 0.2
CORTES_PROVISORIOS = True


class ConsensoError(RuntimeError):
    """Insumo corrompido. Sempre levanta — comparação não se inventa."""


def _jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def _regime(erro_absoluto: float) -> str:
    if erro_absoluto >= CHOQUE_MAIOR:
        return "choque_maior"
    if erro_absoluto >= CHOQUE_MODERADO:
        return "choque_moderado"
    return "normal"


def parear(
    *,
    vintages: Path = VINTAGE_PADRAO,
    resolucoes: Path = RESOLUCOES_PADRAO,
) -> list[dict[str, Any]]:
    """Cruza consenso vigente ANTES do fato com o valor que a fonte publicou.

    O pareamento é por ``mes_referencia``. Vintage sem liquidação correspondente
    (mês ainda aberto) e liquidação sem vintage (mês anterior ao início do
    arquivamento) simplesmente não formam par — e a ausência é reportada, não
    preenchida.
    """
    # a chave é (área, mês) — nunca só o mês
    por_area_e_mes: dict[tuple[str, str], dict[str, Any]] = {}
    for linha in _jsonl(resolucoes):
        mes = str(linha.get("mes_referencia", "")) or str(linha.get("claim_id", "")).split("::")[-1]
        area = str(linha.get("market_area_id", ""))
        if mes and area and linha.get("valor_observado") is not None:
            por_area_e_mes[(area, mes)] = linha

    pares = []
    for vintage in _jsonl(vintages):
        mes = str(vintage.get("mes_referencia", ""))
        indicador = str(vintage.get("indicador", ""))
        area_do_vintage = AREA_DO_INDICADOR.get(indicador)
        if area_do_vintage is None:
            # indicador sem área declarada não pareia com nada: parear às cegas
            # é como o erro fabricado nasce
            continue
        realizado = por_area_e_mes.get((area_do_vintage, mes))
        if realizado is None:
            continue
        mediana = float(vintage["mediana"])
        observado = float(realizado["valor_observado"])
        erro = abs(mediana - observado)
        pares.append(
            {
                "mes_referencia": mes,
                "indicador": indicador,
                "market_area_id": area_do_vintage,
                "consenso_focus": mediana,
                "data_do_boletim": vintage.get("data_do_boletim"),
                "vintage_id": vintage.get("vintage_id"),
                "valor_observado": observado,
                "erro_absoluto_focus": round(erro, 4),
                "regime": _regime(erro),
                "nossa_probabilidade": realizado.get("probability"),
                "outcome": realizado.get("outcome"),
            }
        )
    return sorted(pares, key=lambda p: str(p["mes_referencia"]))


def medir(
    *,
    vintages: Path = VINTAGE_PADRAO,
    resolucoes: Path = RESOLUCOES_PADRAO,
) -> dict[str, Any]:
    """Mede o erro do consenso. Abaixo da amostra mínima, RECUSA agregar.

    O snapshot não tem relógio: a identidade é o conjunto de pares, para que a
    selagem seja idempotente como no resto do projeto.
    """
    pares = parear(vintages=vintages, resolucoes=resolucoes)
    n = len(pares)

    base: dict[str, Any] = {
        "versao": 1,
        "n": n,
        "amostra_minima": AMOSTRA_MINIMA,
        "pares": pares,
        "dependencia_declarada": (
            "O gerador WPAM usa o Focus como sinal dominante (peso 20 contra 10 do IPCA-15): "
            "a nossa probabilidade DERIVA do consenso. Portanto NENHUM resultado aqui pode ser "
            "lido como superação do consenso — isso exigiria sinal independente, que ainda não "
            "existe. O que se mede é a linha de base do próprio Focus."
        ),
        "cortes_de_regime": {
            "moderado_pp": CHOQUE_MODERADO,
            "maior_pp": CHOQUE_MAIOR,
            "provisorios": CORTES_PROVISORIOS,
            "nota": (
                "cortes PROVISÓRIOS — calibrar na variância do IPCA exige amostra que ainda não "
                "existe; importar o corte de outra economia traria a variância dela junto"
            ),
        },
    }

    if n < AMOSTRA_MINIMA:
        base["mae_focus"] = None
        base["por_regime"] = None
        base["suficiente"] = False
        base["metodo"] = (
            f"amostra insuficiente: {n} par(es) contra mínimo de {AMOSTRA_MINIMA}. "
            "Nenhuma estatística agregada é emitida — com poucos meses, MAE e taxa de acerto "
            "dizem mais sobre o acaso do que sobre o previsor, e número publicado é lido como "
            "se valesse. Os pares brutos ficam visíveis; o agregado, não."
        )
        return base

    erros = [float(p["erro_absoluto_focus"]) for p in pares]
    por_regime: dict[str, dict[str, Any]] = {}
    for regime in ("normal", "choque_moderado", "choque_maior"):
        do_regime = [float(p["erro_absoluto_focus"]) for p in pares if p["regime"] == regime]
        por_regime[regime] = {
            "n": len(do_regime),
            "mae": round(sum(do_regime) / len(do_regime), 4) if do_regime else None,
        }

    base["mae_focus"] = round(sum(erros) / len(erros), 4)
    base["por_regime"] = por_regime
    base["suficiente"] = True
    base["metodo"] = (
        "MAE do consenso Focus (vintage, não revisado) contra o valor publicado pela fonte "
        "oficial, por mês pareado; estratificado por regime de surpresa. É a LINHA DE BASE — "
        "ver dependencia_declarada antes de interpretar qualquer comparação."
    )
    return base


def selar(sdk: Any, snapshot: dict[str, Any] | None = None, *, eventos: Path | None = None) -> dict[str, Any]:
    """Sela a medição do consenso na corrente. Mesmo conjunto de pares = dedupe."""
    from asus_theye.audit.schema import hash_json
    from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

    snap = snapshot or medir()
    identidade = hash_json({"pares": snap["pares"], "n": snap["n"]})
    return selar_registro(
        sdk,
        snap,
        tipo_evento="market.consensus_benchmark",
        recurso="consensus_benchmark",
        correlation_id=f"consenso:{identidade[:32]}",
        eventos=eventos or EVENTOS_PADRAO,
    )
