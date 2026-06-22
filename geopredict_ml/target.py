from __future__ import annotations

from itertools import product
from typing import Any

from .business import BusinessProfile
from .geo import clamp


MODEL_FEATURES = (
    "traffic_potential",
    "density_score",
    "norm_competition",
    "competition_penalty",
    "market_validation",
    "residential_score",
    "transport_score",
    "retail_anchor_score",
    "office_score",
    "education_score",
)


def proxy_location_success(features: dict[str, Any], profile: BusinessProfile) -> float:
    score = 0.18
    for name, weight in profile.target_weights.items():
        score += weight * float(features.get(name, 0.0))
    return clamp(score)


def reference_training_rows(profile: BusinessProfile) -> tuple[list[dict[str, float]], list[float]]:
    rows: list[dict[str, float]] = []
    targets: list[float] = []
    values = (0.0, 0.25, 0.5, 0.75, 1.0)
    compact_values = (0.0, 0.5, 1.0)

    for traffic, density, competition, residential, transport, retail in product(
        values, compact_values, compact_values, values, values, values
    ):
        competition_penalty = max(0.0, competition - 0.45)
        market_validation = min(1.0, competition * 1.5)
        row = {
            "traffic_potential": traffic,
            "density_score": density,
            "norm_competition": competition,
            "competition_penalty": competition_penalty,
            "market_validation": market_validation,
            "residential_score": residential,
            "transport_score": transport,
            "retail_anchor_score": retail,
            "office_score": min(1.0, (density + traffic) / 2.0),
            "education_score": min(1.0, traffic * 0.7),
        }
        rows.append(row)
        targets.append(proxy_location_success(row, profile))
    return rows, targets
