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
from datetime import datetime, timezone
from typing import Any

from asus_theye.markets.claim import UNDECLARED_SOURCE, MarketClaim, _is_forbidden


class ResolutionError(RuntimeError):
    """Tentativa de liquidar contra fonte errada, ausente ou proibida. Sempre levanta."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Resolution:
    """Desfecho medido de uma afirmação contra a fonte oficial nomeada."""

    claim_id: str
    market_area_id: str
    outcome: int  # 0 ou 1 — o desfecho observado no mundo
    resolution_source: str
    resolved_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "market_area_id": self.market_area_id,
            "outcome": self.outcome,
            "resolution_source": self.resolution_source,
            "resolved_at": self.resolved_at,
        }


def resolve(claim: MarketClaim, *, outcome: int, source: str, resolved_at: str | None = None) -> Resolution:
    """Liquida a afirmação contra a fonte oficial. Levanta se algo não bate."""
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

    return Resolution(
        claim_id=claim.claim_id,
        market_area_id=claim.market_area_id,
        outcome=int(outcome),
        resolution_source=claim.resolution_source,
        resolved_at=resolved_at or _now(),
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
