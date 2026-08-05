"""Validação independente e somente-leitura da QKP da taxonomia.

A instância tem pesos unitários e sinergia positiva apenas entre áreas do mesmo
grupo. Para k escolhas em um grupo, escolher os k maiores valores é ótimo. Uma
programação dinâmica distribui o limite inteiro de vagas entre os 22 grupos e
obtém o ótimo global sem enumerar 2^138 subconjuntos.
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNAL = ROOT / "reports/commercial/sinal_taxonomia.json"
REFERENCE = ROOT / "reports/commercial/otimo_referencia.json"
TAXONOMY = ROOT / "data/legal-taxonomy/legal_areas.master.json"
CAPACITY_PCT = 0.10
SYNERGY = 3.0


def group_options(areas: list[dict], capacity: int) -> list[tuple[float, list[str]]]:
    ordered = sorted(areas, key=lambda area: area["mencoes"], reverse=True)
    options: list[tuple[float, list[str]]] = []
    for k in range(min(capacity, len(ordered)) + 1):
        chosen = ordered[:k]
        base = sum(area["mencoes"] for area in chosen)
        pair = sum(
            min(chosen[i]["mencoes"], chosen[j]["mencoes"])
            for i in range(k)
            for j in range(i + 1, k)
        )
        options.append((base + SYNERGY * pair, [a["legal_area_id"] for a in chosen]))
    return options


def exact_solution(areas: list[dict], capacity: int, exclude_suspect: bool = False):
    groups: dict[str, list[dict]] = defaultdict(list)
    for area in areas:
        if area.get("mencoes") is None:
            continue
        if exclude_suspect and area.get("suspeita_termo_generico"):
            continue
        groups[area["group"]].append(area)

    dp: dict[int, tuple[float, list[str]]] = {0: (0.0, [])}
    for group in sorted(groups):
        next_dp: dict[int, tuple[float, list[str]]] = {}
        for used, (value, selected) in dp.items():
            for k, (group_value, group_selected) in enumerate(
                group_options(groups[group], capacity)
            ):
                total = used + k
                if total > capacity:
                    break
                candidate = (value + group_value, selected + group_selected)
                if total not in next_dp or candidate[0] > next_dp[total][0]:
                    next_dp[total] = candidate
        dp = next_dp
    return max(dp.items(), key=lambda item: item[1][0])


def objective(areas: list[dict], selected_ids: set[str]) -> float:
    selected = [area for area in areas if area["legal_area_id"] in selected_ids]
    base = sum(area["mencoes"] for area in selected)
    pair = sum(
        min(left["mencoes"], right["mencoes"])
        for index, left in enumerate(selected)
        for right in selected[index + 1 :]
        if left["group"] == right["group"]
    )
    return base + SYNERGY * pair


def self_test_exact_solution(cases: int = 50) -> None:
    rng = random.Random(20260805)
    for case in range(cases):
        size = rng.randint(3, 10)
        capacity = rng.randint(1, min(4, size))
        areas = [
            {
                "legal_area_id": f"case-{case}-area-{index}",
                "group": f"group-{rng.randrange(3)}",
                "mencoes": rng.randrange(25),
            }
            for index in range(size)
        ]
        _, (dp_value, _) = exact_solution(areas, capacity)
        brute_value = max(
            objective(areas, {area["legal_area_id"] for area in chosen})
            for count in range(capacity + 1)
            for chosen in combinations(areas, count)
        )
        if dp_value != brute_value:
            raise AssertionError(
                f"DP divergiu da força bruta no caso {case}: "
                f"{dp_value} != {brute_value}"
            )


def main() -> None:
    self_test_exact_solution()
    signal = json.loads(SIGNAL.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    areas = signal["areas"]
    taxonomy_by_id = {area["legal_area_id"]: area for area in taxonomy["areas"]}
    signal_by_id = {area["legal_area_id"]: area for area in areas}
    capacity = math.floor(
        sum(area.get("mencoes") is not None for area in areas) * CAPACITY_PCT
    )
    used, (optimum, selected) = exact_solution(areas, capacity)
    _, (clean_optimum, clean_selected) = exact_solution(
        areas, capacity, exclude_suspect=True
    )
    selected_base = sum(signal_by_id[area_id]["mencoes"] for area_id in selected)
    suspect_base = sum(
        signal_by_id[area_id]["mencoes"]
        for area_id in selected
        if signal_by_id[area_id].get("suspeita_termo_generico")
    )

    result = {
        "rows": len(areas),
        "unique_areas": len(signal_by_id),
        "taxonomy_area_count": len(taxonomy_by_id),
        "missing_taxonomy_ids": sorted(taxonomy_by_id.keys() - signal_by_id.keys()),
        "unexpected_signal_ids": sorted(signal_by_id.keys() - taxonomy_by_id.keys()),
        "group_mismatches": sorted(
            area_id
            for area_id in taxonomy_by_id.keys() & signal_by_id.keys()
            if taxonomy_by_id[area_id]["group"] != signal_by_id[area_id]["group"]
        ),
        "dp_self_test_cases": 50,
        "missing": sum(area.get("mencoes") is None for area in areas),
        "zeros": sum(area.get("mencoes") == 0 for area in areas),
        "positive": sum((area.get("mencoes") or 0) > 0 for area in areas),
        "suspect": sum(bool(area.get("suspeita_termo_generico")) for area in areas),
        "effective_capacity": capacity,
        "selected_count": used,
        "exact_optimum": optimum,
        "annealing_best": reference["melhor_encontrado"],
        "annealing_matches_exact": reference["melhor_encontrado"] == optimum,
        "selected": sorted(selected),
        "selected_suspect_count": sum(
            bool(signal_by_id[area_id].get("suspeita_termo_generico"))
            for area_id in selected
        ),
        "selected_suspect_base_share": suspect_base / selected_base,
        "exact_without_suspect_terms": clean_optimum,
        "value_drop_without_suspect_terms": 1 - clean_optimum / optimum,
        "selected_without_suspect_terms": sorted(clean_selected),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
