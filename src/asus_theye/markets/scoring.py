# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Score — Brier e skill contra baseline, com a janela sempre declarada.

O número que importa não é a probabilidade, é o **erro medido** contra o
desfecho. Quatro regras estruturais, cada uma fechando um jeito de o score
mentir:

1. **Brier é ``None`` até liquidar, nunca 0.** Sem par (probabilidade, desfecho)
   não há erro a medir. Zero seria uma medição falsa de perfeição.
2. **Skill exige baseline.** ``skill_score = 1 - brier_modelo / brier_baseline``.
   O baseline é um palpite constante — a taxa-base do desfecho, ou uma taxa
   histórica declarada. Um modelo que não bate o palpite constante não tem skill.
3. **A janela viaja sempre junto.** ``window`` é obrigatória: quantos contratos,
   de qual recorte. Uma manchete de Brier sem janela mente por omissão (o
   ``voto_legislativo`` a 0,0033 são 40 contratos de UMA votação).
4. **Se o baseline vence, publica.** Quando ``skill_score <= 0`` o resultado diz
   ``baseline_beats_model=True`` em vez de esconder — é a regra 4 do AGENTS.md
   aplicada ao próprio número de vitrine.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class ScoringError(RuntimeError):
    """Entrada inválida para o score. Sempre levanta — nunca degrada em silêncio."""


Pair = tuple[float, int]  # (probabilidade em [0,1], desfecho em {0,1})


def _validate_pairs(pairs: Sequence[Pair]) -> None:
    for i, pair in enumerate(pairs):
        if len(pair) != 2:
            raise ScoringError(f"par {i}: esperado (probabilidade, desfecho), veio {pair!r}")
        prob, outcome = pair
        if isinstance(prob, bool) or not isinstance(prob, (int, float)) or not 0.0 <= float(prob) <= 1.0:
            raise ScoringError(f"par {i}: probabilidade deve estar em [0,1], veio {prob!r}")
        if isinstance(outcome, bool) or outcome not in (0, 1):
            raise ScoringError(f"par {i}: desfecho deve ser 0 ou 1, veio {outcome!r}")


def brier_score(pairs: Sequence[Pair]) -> float | None:
    """Brier = média de ``(probabilidade - desfecho)²``.

    Devolve ``None`` para conjunto vazio: nada liquidado, nada a medir. Nunca 0.
    """
    _validate_pairs(pairs)
    if not pairs:
        return None
    total = sum((float(prob) - outcome) ** 2 for prob, outcome in pairs)
    return round(total / len(pairs), 6)


def base_rate(outcomes: Sequence[int]) -> float | None:
    """Taxa-base observada (fração de desfechos = 1). ``None`` se vazio."""
    outcomes = list(outcomes)
    for outcome in outcomes:
        if isinstance(outcome, bool) or outcome not in (0, 1):
            raise ScoringError(f"desfecho deve ser 0 ou 1, veio {outcome!r}")
    if not outcomes:
        return None
    return round(sum(outcomes) / len(outcomes), 6)


def skill_score(
    pairs: Sequence[Pair],
    *,
    window: str,
    baseline_probability: float | None = None,
) -> dict[str, Any]:
    """Skill do modelo contra um palpite constante, com a janela declarada.

    ``baseline_probability`` fixa o palpite constante; se ``None``, usa a
    taxa-base observada. A janela (``window``) é obrigatória e viaja no
    resultado — sem ela o número não pode ser lido.
    """
    if not window or not window.strip():
        raise ScoringError(
            "window é obrigatória: um Brier sem a janela declarada (quantos contratos, "
            "de qual recorte) mente por omissão. Ex.: '40 contratos, votação 2637721-10'."
        )
    _validate_pairs(pairs)
    if not pairs:
        raise ScoringError("sem pares liquidados não há skill a medir — Brier é None, não 0")

    outcomes = [outcome for _, outcome in pairs]

    if baseline_probability is None:
        computed = base_rate(outcomes)
        assert computed is not None  # pairs não-vazio garante taxa-base
        baseline = computed
    else:
        if isinstance(baseline_probability, bool) or not 0.0 <= float(baseline_probability) <= 1.0:
            raise ScoringError(f"baseline_probability deve estar em [0,1], veio {baseline_probability!r}")
        baseline = float(baseline_probability)

    # Briers CRUS (sem arredondar) para o guard e a divisão; arredonda-se só na
    # saída. Testar perfeição no valor arredondado marcaria como "perfeito" um
    # baseline apenas quase perfeito (Brier verdadeiro em (0, 5e-7]) — o que
    # emitiria uma ressalva falsa e descartaria uma skill real. Regra: nunca
    # afirmar o que não foi medido.
    raw_model_brier = sum((float(prob) - outcome) ** 2 for prob, outcome in pairs) / len(pairs)
    raw_baseline_brier = sum((baseline - outcome) ** 2 for outcome in outcomes) / len(outcomes)
    model_brier = round(raw_model_brier, 6)
    baseline_brier = round(raw_baseline_brier, 6)

    if raw_baseline_brier == 0.0:
        # Baseline verdadeiramente perfeito (palpite constante no valor exato do
        # desfecho, todos iguais). Não se divide por zero: skill fica indefinida.
        skill: float | None = None
        limitations = [
            "baseline com Brier 0 (palpite constante já perfeito nesta janela): "
            "skill indefinida — o recorte não permite demonstrar habilidade."
        ]
        baseline_beats_model = raw_model_brier > 0.0
    else:
        raw_skill = 1.0 - raw_model_brier / raw_baseline_brier
        skill = round(raw_skill, 6)
        baseline_beats_model = raw_skill <= 0.0
        limitations = []
        if baseline_beats_model:
            limitations.append(
                f"baseline vence o modelo (skill {skill} ≤ 0): um palpite constante em "
                f"{round(baseline, 6)} dá Brier {baseline_brier} contra {model_brier} do modelo. "
                "Regra 4 do AGENTS.md: isto é publicado, não escondido."
            )

    return {
        "n": len(pairs),
        "window": window,
        "model_brier": model_brier,
        "baseline_probability": round(baseline, 6),
        "baseline_brier": baseline_brier,
        "skill_score": skill,
        "baseline_beats_model": baseline_beats_model,
        "limitations": limitations,
    }
