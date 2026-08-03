"""Small, serializable optimization problem used by the benchmark engine."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class BenchmarkProblem:
    """A deterministic binary knapsack problem where a higher score is better."""

    name: str
    values: tuple[float, ...]
    weights: tuple[float, ...]
    capacity: float

    def __post_init__(self) -> None:
        if not self.values or len(self.values) != len(self.weights):
            raise ValueError("values and weights must be non-empty and have equal lengths")
        if self.capacity < 0 or any(weight < 0 for weight in self.weights):
            raise ValueError("capacity and weights must be non-negative")

    @property
    def variable_count(self) -> int:
        return len(self.values)

    def candidates(self) -> Iterator[tuple[int, ...]]:
        return product((0, 1), repeat=self.variable_count)

    def is_feasible(self, bits: tuple[int, ...]) -> bool:
        return sum(weight * bit for weight, bit in zip(self.weights, bits, strict=True)) <= self.capacity

    def score(self, bits: tuple[int, ...]) -> float:
        if len(bits) != self.variable_count or not self.is_feasible(bits):
            return 0.0
        return float(sum(value * bit for value, bit in zip(self.values, bits, strict=True)))

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "values": list(self.values),
            "weights": list(self.weights),
            "capacity": self.capacity,
        }


def load_demo_problem() -> BenchmarkProblem:
    """Return the versioned, immutable demo dataset used by the CLI."""

    return BenchmarkProblem(
        name="demo_portfolio_v1",
        values=(8.0, 11.0, 6.0, 14.0, 7.0, 9.0),
        weights=(4.0, 6.0, 3.0, 8.0, 4.0, 5.0),
        capacity=15.0,
    )
