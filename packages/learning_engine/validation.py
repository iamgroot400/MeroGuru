"""Resource ranking (plan.md 13.2) and plan-level validation checks.

Kept as pure functions with explicit, storable score components so a ranking
decision can always be explained rather than being an opaque model output.
"""
from __future__ import annotations

from dataclasses import dataclass

WEIGHTS = {
    "relevance": 0.25,
    "credibility": 0.15,
    "level_match": 0.15,
    "coverage": 0.10,
    "language_match": 0.10,
    "practical_value": 0.10,
    "duration_match": 0.05,
    "accessibility": 0.05,
    "license_clarity": 0.05,
}


@dataclass
class ResourceScoreInputs:
    relevance: float
    credibility: float
    level_match: float
    coverage: float
    language_match: float
    practical_value: float
    duration_match: float
    accessibility: float
    license_clarity: float
    duplication_penalty: float = 0.0
    availability_penalty: float = 0.0


@dataclass
class ResourceScore:
    total: float
    components: dict[str, float]


def score_resource(inputs: ResourceScoreInputs) -> ResourceScore:
    components = {name: getattr(inputs, name) * weight for name, weight in WEIGHTS.items()}
    total = sum(components.values()) - inputs.duplication_penalty - inputs.availability_penalty
    components["duplication_penalty"] = -inputs.duplication_penalty
    components["availability_penalty"] = -inputs.availability_penalty
    return ResourceScore(total=round(max(0.0, min(1.0, total)), 4), components=components)


def validate_plan_time_budget(daily_estimates: list[int], minutes_per_day: int) -> list[str]:
    """plan.md success criterion: a plan must never exceed the daily budget by >10%."""
    warnings = []
    ceiling = minutes_per_day * 1.10
    for i, estimate in enumerate(daily_estimates):
        if estimate > ceiling:
            warnings.append(f"day {i}: {estimate}min exceeds the {minutes_per_day}min budget by more than 10%")
    return warnings
