"""Métricas por nicho — com denominador, amostra e limitações.

A regra que atravessa o projeto inteiro aparece aqui na forma comercial: uma
taxa de conversão de 100% sobre 2 oportunidades **não** é melhor que 40% sobre
200. ``sample_sufficient`` é o campo que impede essa leitura, e ``rank_niches``
separa fisicamente os nichos com amostra suficiente dos demais — em vez de
misturá-los numa lista única que convidaria à comparação errada.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import Any

MINIMUM_SAMPLE = 8
"""Fechamentos mínimos para a taxa ser ranqueável. Abaixo disso é ruído."""

TICKET_BANDS_BRL: dict[str, tuple[float, float]] = {
    "baixo": (0.0, 15_000.0),
    "medio": (15_000.0, 80_000.0),
    "alto": (80_000.0, float("inf")),
}
"""Faixas de ticket. Servem só para CONFRONTAR o que foi declarado com o medido."""


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _cycle_days(opportunity: dict[str, Any]) -> float | None:
    if not opportunity.get("closed_at"):
        return None
    delta = _parse(opportunity["closed_at"]) - _parse(opportunity["created_at"])
    return round(delta.total_seconds() / 86400, 2)


def observed_band(average_ticket: float | None) -> str | None:
    """Faixa em que o ticket medido caiu. ``None`` quando não há ticket medido."""
    if average_ticket is None:
        return None
    for band, (low, high) in TICKET_BANDS_BRL.items():
        if low <= average_ticket < high:
            return band
    return None


def reality_check(
    metrics: dict[str, Any], niche: dict[str, Any], *, minimum_sample: int = MINIMUM_SAMPLE
) -> dict[str, Any]:
    """Confronta o que você DECLAROU com o que os dados mostram.

    A expectativa declarada não é um palpite a ser escondido — é uma hipótese a
    ser testada. Quando os dados a contrariam com amostra suficiente, isso é a
    informação mais útil do painel. Quando a amostra é pequena, o veredito é
    ``insufficient_evidence``: a hipótese sobrevive por falta de prova, não por
    estar certa.
    """
    declared = niche.get("ticket_band_declared")
    observed = observed_band(metrics.get("average_ticket_brl"))

    if observed is None:
        verdict, note = "no_data", "nenhum ganho com valor registrado — nada a confrontar"
    elif not metrics["sample_sufficient"]:
        verdict = "insufficient_evidence"
        note = (
            f"observado {observed!r} sobre {metrics['denominator']} fechamento(s): "
            f"pouco para contrariar a expectativa {declared!r}"
        )
    elif declared == observed:
        verdict, note = "confirmed", f"expectativa {declared!r} confirmada pelos dados"
    else:
        verdict = "contradicted"
        note = (
            f"você declarou ticket {declared!r}, mas o medido é {observed!r} "
            f"(R$ {metrics['average_ticket_brl']:,.0f} sobre {metrics['denominator']} fechamentos)"
        )

    return {
        "niche_id": niche["niche_id"],
        "priority_declared": niche.get("priority"),
        "ticket_band_declared": declared,
        "ticket_band_observed": observed,
        "average_ticket_brl": metrics.get("average_ticket_brl"),
        "denominator": metrics["denominator"],
        "verdict": verdict,
        "note": note,
        "claim_class": "DERIVED_METRIC",
    }


def compute_metrics(
    opportunities: list[dict[str, Any]],
    niche_id: str,
    *,
    period_start: str,
    period_end: str,
    minimum_sample: int = MINIMUM_SAMPLE,
) -> dict[str, Any]:
    """Métricas de um nicho. Denominador zero produz taxa ``None``, nunca 0%."""
    scoped = [o for o in opportunities if o["niche_id"] == niche_id]
    won = [o for o in scoped if o["stage"] == "ganho"]
    lost = [o for o in scoped if o["stage"] == "perdido"]
    open_ = [o for o in scoped if o["stage"] not in ("ganho", "perdido")]

    denominator = len(won) + len(lost)
    win_rate = round(len(won) / denominator, 4) if denominator else None
    sample_sufficient = denominator >= minimum_sample

    valued = [o["value_brl"] for o in won if o.get("value_brl") is not None]
    revenue = round(sum(valued), 2) if valued else None
    average_ticket = round(revenue / len(valued), 2) if revenue is not None else None

    cycles = [c for c in (_cycle_days(o) for o in won + lost) if c is not None]
    median_cycle = round(statistics.median(cycles), 2) if cycles else None

    lost_reasons: dict[str, int] = {}
    for opportunity in lost:
        reason = opportunity.get("lost_reason", "outro")
        lost_reasons[reason] = lost_reasons.get(reason, 0) + 1

    limitations = []
    if denominator == 0:
        limitations.append("nenhuma oportunidade fechada no período — não há taxa de conversão a calcular")
    elif not sample_sufficient:
        limitations.append(
            f"amostra insuficiente: {denominator} fechamento(s), mínimo {minimum_sample}. "
            "A taxa é exibida mas não é ranqueável nem comparável"
        )
    else:
        limitations.append(f"taxa calculada sobre {denominator} fechamentos no período")
    if len(valued) < len(won):
        limitations.append(
            f"{len(won) - len(valued)} de {len(won)} ganhos sem valor registrado — receita e ticket médio são parciais"
        )
    if not cycles:
        limitations.append("nenhum ciclo completo — tempo mediano indisponível")

    return {
        "niche_id": niche_id,
        "period_start": period_start,
        "period_end": period_end,
        "opportunities_total": len(scoped),
        "won": len(won),
        "lost": len(lost),
        "open": len(open_),
        "win_rate": win_rate,
        "denominator": denominator,
        "sample_sufficient": sample_sufficient,
        "minimum_sample": minimum_sample,
        "revenue_brl": revenue,
        "average_ticket_brl": average_ticket,
        "median_cycle_days": median_cycle,
        "lost_reasons": dict(sorted(lost_reasons.items())),
        "limitations": limitations,
        "claim_class": "DERIVED_METRIC",
        "computed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def rank_niches(
    opportunities: list[dict[str, Any]],
    niche_ids: list[str],
    *,
    period_start: str,
    period_end: str,
    by: str = "win_rate",
    minimum_sample: int = MINIMUM_SAMPLE,
) -> dict[str, Any]:
    """Ranqueia nichos, separando os que têm amostra suficiente dos que não têm.

    A separação é física, não uma nota de rodapé: quem não tem amostra aparece
    em outra lista. Misturá-los convidaria exatamente à comparação errada que a
    métrica existe para evitar.
    """
    if by not in ("win_rate", "revenue_brl", "average_ticket_brl", "opportunities_total"):
        raise ValueError(f"critério de ranking desconhecido: {by!r}")

    metrics = [
        compute_metrics(
            opportunities,
            niche_id,
            period_start=period_start,
            period_end=period_end,
            minimum_sample=minimum_sample,
        )
        for niche_id in niche_ids
    ]

    rankable = [m for m in metrics if m["sample_sufficient"] and m.get(by) is not None]
    insufficient = [m for m in metrics if not m["sample_sufficient"]]
    no_data = [m for m in metrics if m["sample_sufficient"] and m.get(by) is None]

    rankable.sort(key=lambda m: m[by], reverse=True)
    insufficient.sort(key=lambda m: m["denominator"], reverse=True)

    return {
        "criterion": by,
        "period_start": period_start,
        "period_end": period_end,
        "minimum_sample": minimum_sample,
        "ranked": rankable,
        "insufficient_sample": insufficient,
        "no_data_for_criterion": no_data,
        "note": (
            f"{len(rankable)} de {len(metrics)} nichos têm amostra suficiente "
            f"(≥{minimum_sample} fechamentos) para ranquear por {by}. "
            "Os demais aparecem separados de propósito: uma taxa sobre poucos "
            "fechamentos não é comparável a uma sobre muitos."
        ),
        "claim_class": "DERIVED_METRIC",
        "computed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
