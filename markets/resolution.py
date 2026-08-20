# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Resolução — liquidar uma afirmação contra a fonte oficial, e só ela.

Liquidar é o ato que separa previsão de palpite: a pergunta binária encontra o
desfecho real, medido contra a **fonte nomeada** que a área declarou. Três
regras estruturais:

1. **Resolve contra a fonte da afirmação, ou levanta.** A ``source`` passada
   tem de ser exatamente a ``resolution_source`` da afirmação. Resolver contra
   outra coisa mediria acerto contra o mundo errado.
2. **Fonte ``"a declarar"`` não liquida.** Sem fonte oficial escolhida não há o
   que medir — a resolução levanta em vez de inventar um desfecho. UNKNOWN over
   guess, de novo.
3. **Kalshi nunca resolve.** Ela entra só por :func:`record_comparator`, que
   registra a divergência entre a nossa probabilidade e o preço dela — e deixa
   explícito que quem acertou só se sabe **depois** que o evento liquida contra
   a fonte oficial.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from asus_theye.markets.claim import UNDECLARED_SOURCE, MarketClaim, _is_forbidden


class ResolutionError(RuntimeError):
    """Tentativa de liquidar contra fonte errada, ausente ou proibida. Sempre levanta."""


def _hoje() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# COMO sabemos que o desfecho ficou determinado. O número nunca viaja sem o
# método — e aqui o método muda o que o número significa.
#
# "primeira_observacao": vimos o valor presente na fonte NESTE dia. É um LIMITE
#   SUPERIOR provável da publicação: o dado existia neste instante ou antes.
#   Não é a data de publicação, e chamá-la assim seria mentira — a API do SGS
#   devolve o PERÍODO DE REFERÊNCIA (01/07/2026 = IPCA de julho), nunca quando
#   o IBGE publicou. Com o cron diário a folga é de no máximo um dia.
# "calendario_da_fonte": a data veio do calendário oficial de divulgação. Mais
#   apertado, e o campo já existe para que a história possa MELHORAR depois sem
#   ser reescrita.
# "desconhecida": dado LEGADO (import retrospectivo). O banco de origem só traz
#   resolved_at; quando a fonte publicou é informação que nunca tivemos. A data
#   fica preenchida com o melhor que existe, mas a base grita que ela NÃO serve
#   para re-ancorar horizonte — a calibração tem de excluir ou separar estes
#   pontos, e não pode fazer isso se a ignorância não estiver declarada.
BASE_PRIMEIRA_OBSERVACAO = "primeira_observacao"
BASE_CALENDARIO = "calendario_da_fonte"
BASE_DESCONHECIDA = "desconhecida"
BASES_DE_DETERMINACAO = (BASE_PRIMEIRA_OBSERVACAO, BASE_CALENDARIO, BASE_DESCONHECIDA)
# As únicas bases em que o horizonte re-ancorado significa alguma coisa.
BASES_CONFIAVEIS = (BASE_PRIMEIRA_OBSERVACAO, BASE_CALENDARIO)


@dataclass(frozen=True)
class Resolution:
    """Desfecho medido de uma afirmação contra a fonte oficial nomeada."""

    claim_id: str
    market_area_id: str
    outcome: int  # 0 ou 1 — o desfecho observado no mundo
    resolution_source: str
    resolved_at: str
    # QUANDO o desfecho ficou determinado no mundo — distinto de resolved_at,
    # que é quando O NOSSO processo rodou. Os dois divergem sempre que a
    # liquidação atrasa, é refeita ou é migrada; e é este, não o deadline nem o
    # resolved_at, o relógio contra o qual a calibração deve medir horizonte.
    determination_date: str
    determination_basis: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "market_area_id": self.market_area_id,
            "outcome": self.outcome,
            "resolution_source": self.resolution_source,
            "resolved_at": self.resolved_at,
            "determination_date": self.determination_date,
            "determination_basis": self.determination_basis,
        }


def resolve(
    claim: MarketClaim,
    *,
    outcome: int,
    source: str,
    resolved_at: str | None = None,
    determination_date: str | None = None,
    determination_basis: str = BASE_PRIMEIRA_OBSERVACAO,
) -> Resolution:
    """Liquida a afirmação contra a fonte oficial. Levanta se algo não bate.

    ``determination_date`` ausente assume o dia de hoje com base
    ``primeira_observacao``: é hoje que estamos vendo o valor na fonte, logo o
    dado existe hoje ou antes. Declarar isso é honesto; chamar de "data de
    publicação" não seria.
    """
    if isinstance(outcome, bool) or outcome not in (0, 1):
        raise ResolutionError(f"outcome deve ser 0 ou 1 (desfecho binário observado), veio {outcome!r}")

    if not claim.resolvable:
        raise ResolutionError(
            f"{claim.claim_id}: área {claim.market_area_id!r} tem fonte {claim.resolution_source!r} "
            f"({UNDECLARED_SOURCE!r} não liquida). Sem fonte oficial nomeada não há desfecho a medir."
        )

    if _is_forbidden(source):
        raise ResolutionError(
            f"{source!r} não pode resolver: preço de mercado é opinião agregada, não desfecho. "
            "Kalshi é comparador (ver record_comparator), nunca fonte de resolução."
        )

    if source != claim.resolution_source:
        raise ResolutionError(
            f"{claim.claim_id}: resolução exige a fonte declarada da área "
            f"({claim.resolution_source!r}), veio {source!r}. Não se troca a fonte na hora de liquidar."
        )

    if determination_basis not in BASES_DE_DETERMINACAO:
        raise ResolutionError(
            f"determination_basis deve ser um de {BASES_DE_DETERMINACAO}, veio {determination_basis!r} "
            "— data sem método declarado não entra"
        )
    determinada = determination_date or _hoje()
    try:
        date.fromisoformat(determinada)
    except (ValueError, TypeError) as exc:
        raise ResolutionError(f"determination_date deve ser data ISO (YYYY-MM-DD), veio {determinada!r}") from exc

    return Resolution(
        claim_id=claim.claim_id,
        market_area_id=claim.market_area_id,
        outcome=int(outcome),
        resolution_source=claim.resolution_source,
        resolved_at=resolved_at or _now(),
        determination_date=determinada,
        determination_basis=determination_basis,
    )


@dataclass(frozen=True)
class ComparatorDivergence:
    """Divergência registrada contra um comparador (ex.: Kalshi). Nunca liquida nada."""

    claim_id: str
    our_probability: float
    comparator: str
    comparator_price: float
    divergence: float  # |nossa probabilidade - preço do comparador|
    recorded_at: str
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "our_probability": self.our_probability,
            "comparator": self.comparator,
            "comparator_price": self.comparator_price,
            "divergence": self.divergence,
            "recorded_at": self.recorded_at,
            "note": self.note,
        }


def record_comparator(
    claim: MarketClaim,
    *,
    comparator_price: float,
    comparator: str = "Kalshi",
    recorded_at: str | None = None,
) -> ComparatorDivergence:
    """Registra a divergência entre a nossa probabilidade e o preço do comparador.

    Kalshi entra **só aqui**. O preço é opinião agregada: serve para registrar
    onde discordamos e, depois que o evento liquidar contra a fonte oficial,
    para dizer quem acertou. Ele nunca vira desfecho.
    """
    if not isinstance(comparator_price, (int, float)) or isinstance(comparator_price, bool):
        raise ResolutionError(f"comparator_price deve ser número em [0,1], veio {comparator_price!r}")
    if not 0.0 <= float(comparator_price) <= 1.0:
        raise ResolutionError(
            f"comparator_price (preço como probabilidade) deve estar em [0,1], veio {comparator_price!r}"
        )

    divergence = abs(claim.probability - float(comparator_price))
    return ComparatorDivergence(
        claim_id=claim.claim_id,
        our_probability=claim.probability,
        comparator=comparator,
        comparator_price=float(comparator_price),
        divergence=round(divergence, 6),
        recorded_at=recorded_at or _now(),
        note=(
            f"{comparator} é comparador, não fonte. Quem acertou só se sabe depois que "
            f"a afirmação liquidar contra {claim.resolution_source!r}."
        ),
    )
