# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Afirmação de mercado — pergunta binária, com prazo e fonte de resolução nomeada.

Um mercado preditivo aqui é uma pergunta de sim/não com data-limite, uma
probabilidade e uma **fonte oficial nomeada** contra a qual o desfecho será
medido. Três regras estruturais, cada uma fechando um jeito de a afirmação
mentir sobre o que é:

1. **A área existe no classificador ou levanta.** ``market_area_id`` é validado
   contra ``data/domains/mercados_preditivos.json`` — enum fechado. Inventar uma
   área (ou escrevê-la errado) levanta em vez de virar um mercado fantasma.
2. **A fonte de resolução vem da área, não do chamador.** Ninguém escolhe
   resolver contra o que quiser: a fonte é a que o classificador declara. Uma
   área cuja fonte ainda é ``"a declarar"`` gera afirmação (estado aberto), mas
   ela nasce ``resolvable=False`` — não há como liquidá-la sem fonte. UNKNOWN
   over guess.
3. **Kalshi nunca é fonte.** O preço de um mercado é opinião agregada, não
   desfecho; resolver contra ele mediria concordância com outra previsão, não
   acerto contra o mundo. Kalshi entra só como comparador (ver ``resolution``).

E o ``limiar de máxima incerteza``: quando ``produtos/_core`` escolhe a mediana
da janela de 12 meses, a probabilidade nasce ~0,50 de propósito. Isso não é
acaso — nesse limiar o produto não consegue demonstrar skill mesmo funcionando.
A afirmação carrega ``max_uncertainty`` para que a leitura não confunda desenho
com sorte.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from asus_theye._pkg_paths import pkg_data

DATA_DIR = pkg_data("data", "domains")
CLASSIFIER = DATA_DIR / "mercados_preditivos.json"

# Fonte ainda não escolhida: gera mercado, mas não resolve.
UNDECLARED_SOURCE = "a declarar"
# Kalshi é comparador, nunca resolvedor — proibido como fonte, estruturalmente.
FORBIDDEN_SOURCES = ("kalshi",)
# Tolerância para marcar o limiar de máxima incerteza (mediana da janela).
UNCERTAINTY_TOLERANCE = 1e-9


class MarketClaimError(RuntimeError):
    """Entrada inválida para uma afirmação de mercado. Sempre levanta — nunca degrada."""


def load_classifier() -> dict[str, Any]:
    """Lê o classificador de mercados preditivos (a única fonte de áreas válidas)."""
    return json.loads(CLASSIFIER.read_text(encoding="utf-8"))


def load_areas() -> dict[str, dict[str, Any]]:
    """Mapa ``market_area_id -> área`` a partir do classificador."""
    return {area["market_area_id"]: area for area in load_classifier()["areas"]}


def resolution_source_for(market_area_id: str, *, areas: dict[str, dict[str, Any]] | None = None) -> str:
    """Fonte de resolução declarada para a área. Levanta se a área não existe."""
    areas = areas if areas is not None else load_areas()
    if market_area_id not in areas:
        raise MarketClaimError(
            f"market_area_id desconhecido: {market_area_id!r}. "
            f"Enum fechado — áreas válidas: {sorted(areas)}. "
            f"Área nova entra pelo classificador (data/domains/mercados_preditivos.json), não aqui."
        )
    return str(areas[market_area_id]["fonte_resolucao"])


def _is_forbidden(source: str) -> bool:
    lowered = source.strip().lower()
    return any(bad in lowered for bad in FORBIDDEN_SOURCES)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class MarketClaim:
    """Uma pergunta binária com prazo, probabilidade e fonte de resolução nomeada."""

    claim_id: str
    market_area_id: str
    question: str
    deadline: str  # data ISO (YYYY-MM-DD) do fechamento da pergunta
    probability: float  # P(desfecho = 1), em [0, 1]
    resolution_source: str  # herdada da área; nunca Kalshi
    created_at: str
    max_uncertainty: bool  # True quando a probabilidade nasce no limiar ~0,50

    @property
    def resolvable(self) -> bool:
        """Só é liquidável contra fonte nomeada. ``"a declarar"`` não resolve."""
        return self.resolution_source != UNDECLARED_SOURCE and not _is_forbidden(self.resolution_source)

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "market_area_id": self.market_area_id,
            "question": self.question,
            "deadline": self.deadline,
            "probability": self.probability,
            "resolution_source": self.resolution_source,
            "created_at": self.created_at,
            "max_uncertainty": self.max_uncertainty,
            "resolvable": self.resolvable,
        }


def _validate_iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise MarketClaimError(f"{field} deve ser data ISO (YYYY-MM-DD), veio {value!r}") from exc


def make_claim(
    *,
    claim_id: str,
    market_area_id: str,
    question: str,
    deadline: str,
    probability: float,
    created_at: str | None = None,
    areas: dict[str, dict[str, Any]] | None = None,
) -> MarketClaim:
    """Cria uma afirmação de mercado válida ou levanta.

    A ``resolution_source`` é sempre derivada da área no classificador — o
    chamador não escolhe contra o que resolver, o que torna impossível apontar
    Kalshi como fonte por acidente.
    """
    if not claim_id or not claim_id.strip():
        raise MarketClaimError("claim_id é obrigatório")
    if not question or not question.strip():
        raise MarketClaimError("question é obrigatória — uma pergunta binária precisa ser enunciada")
    if not isinstance(probability, (int, float)) or isinstance(probability, bool):
        raise MarketClaimError(f"probability deve ser número em [0,1], veio {probability!r}")
    if not 0.0 <= float(probability) <= 1.0:
        raise MarketClaimError(f"probability deve estar em [0,1], veio {probability!r}")

    source = resolution_source_for(market_area_id, areas=areas)
    # Guarda extra: mesmo que o classificador algum dia registre Kalshi como
    # fonte, a criação recusa. A doutrina é mais forte que o dado.
    if _is_forbidden(source):
        raise MarketClaimError(
            f"{market_area_id}: fonte {source!r} é proibida como resolvedor. "
            "Kalshi é comparador, nunca fonte de resolução (ver markets.resolution)."
        )

    created = created_at or _now()
    created_day = _validate_iso_date(created[:10], "created_at")
    deadline_day = _validate_iso_date(deadline, "deadline")
    if deadline_day < created_day:
        raise MarketClaimError(f"deadline {deadline} não pode ser anterior à criação {created[:10]}")

    max_uncertainty = abs(float(probability) - 0.5) <= UNCERTAINTY_TOLERANCE

    return MarketClaim(
        claim_id=claim_id,
        market_area_id=market_area_id,
        question=question,
        deadline=deadline,
        probability=float(probability),
        resolution_source=source,
        created_at=created,
        max_uncertainty=max_uncertainty,
    )
