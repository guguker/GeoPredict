from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .business import get_business_profile
from .explain import build_explanation
from .features import compute_cell_features, normalize_geojson_pois, saturating_count
from .geo import clamp
from .grid import GridCell, polygon_to_grid_cells, validate_polygon_geometry
from .model import GradientBoostingRegressorLite, train_reference_model


def analyze_request(
    request_payload: dict[str, Any],
    pois_geojson: dict | None = None,
    model_path: str | Path | None = None,
    max_cells: int = 1_000,
    data_sources: list[str] | None = None,
    data_warnings: list[str] | None = None,
) -> dict[str, Any]:
    geometry = request_payload.get("geometry")
    validate_polygon_geometry(geometry)

    business_type = request_payload.get("business_type")
    if not business_type:
        raise ValueError("business_type is required")

    resolution = int(request_payload.get("h3_resolution", 9))
    profile = get_business_profile(str(business_type))
    cells = polygon_to_grid_cells(geometry, resolution=resolution, max_cells=max_cells)
    pois = normalize_geojson_pois(pois_geojson)
    resolved_data_sources = data_sources if data_sources is not None else (["osm"] if pois_geojson else [])
    resolved_data_warnings = data_warnings or []
    feature_rows = [compute_cell_features(cell, pois, profile) for cell in cells]
    model = _load_or_train_model(profile, model_path)
    model_predictions = model.predict(feature_rows)
    candidate_scores = [_candidate_score(row, score) for row, score in zip(feature_rows, model_predictions)]
    ranked_predictions = _rank_candidates(cells, feature_rows, candidate_scores)

    features = []
    for cell, row, raw_score, candidate in zip(cells, feature_rows, model_predictions, candidate_scores):
        rank_info = ranked_predictions[cell.h3_id]
        recommendation = _recommendation_for_candidate(candidate, rank_info["rank"], len(cells))
        properties = {
            "h3_id": cell.h3_id,
            "rank": rank_info["rank"],
            "top_percentile": round(rank_info["rank"] / max(1, len(cells)), 4),
            "suitability": round(candidate["selection_score"], 3),
            "success_probability": round(candidate["selection_score"], 3),
            "model_score": round(raw_score, 3),
            "selection_score": round(candidate["selection_score"], 3),
            "data_confidence": round(candidate["data_confidence"], 3),
            "recommendation": recommendation["code"],
            "recommendation_label": recommendation["label"],
            "competition": row["competition"],
            "norm_competition": round(float(row["norm_competition"]), 3),
            "competition_penalty": round(float(row["competition_penalty"]), 3),
            "market_validation": round(float(row["market_validation"]), 3),
            "traffic_potential": round(float(row["traffic_potential"]), 3),
            "density_score": round(float(row["density_score"]), 3),
            "poi_counts": row["poi_counts"],
            "explanation": build_explanation(row, candidate["selection_score"], profile),
        }
        features.append({"type": "Feature", "geometry": cell.geometry, "properties": properties})

    selection_scores = [candidate["selection_score"] for candidate in candidate_scores]
    avg_suitability = round(sum(selection_scores) / len(selection_scores), 3) if selection_scores else 0.0
    avg_model_score = round(sum(model_predictions) / len(model_predictions), 3) if model_predictions else 0.0
    grid_backend = cells[0].backend if cells else "unknown"
    top_candidates = _top_candidates(cells, model_predictions, candidate_scores, ranked_predictions)
    recommendation_counts = _recommendation_counts(cells, candidate_scores, ranked_predictions)

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_hexagons": len(features),
            "h3_resolution": resolution,
            "avg_suitability": avg_suitability,
            "avg_model_score": avg_model_score,
            "business_type": profile.business_type,
            "data_sources": resolved_data_sources,
            "data_status": _data_status(resolved_data_sources, resolved_data_warnings),
            "data_warnings": resolved_data_warnings,
            "poi_count": len(pois),
            "model_active": True,
            "model_type": model.model_type,
            "model_version": model.model_version,
            "target_type": "proxy_location_success",
            "grid_backend": grid_backend,
            "top_candidates": top_candidates,
            "recommendation_counts": recommendation_counts,
            "selection_policy": "strict_v2_rank_confidence_saturation",
        },
    }


def _load_or_train_model(profile: Any, model_path: str | Path | None) -> GradientBoostingRegressorLite:
    if model_path and Path(model_path).exists():
        return GradientBoostingRegressorLite.load(model_path)
    return train_reference_model(profile)


def _data_status(data_sources: list[str], data_warnings: list[str]) -> str:
    if data_warnings or "osm_unavailable" in data_sources:
        return "degraded"
    if data_sources:
        return "live"
    return "empty"


def _candidate_score(features: dict[str, Any], model_score: float) -> dict[str, float]:
    traffic = float(features.get("traffic_potential", 0.0))
    density = float(features.get("density_score", 0.0))
    residential = float(features.get("residential_score", 0.0))
    transport = float(features.get("transport_score", 0.0))
    retail = float(features.get("retail_anchor_score", 0.0))
    office = float(features.get("office_score", 0.0))
    nearby_total = float(features.get("nearby_poi_total", 0.0))
    norm_competition = float(features.get("norm_competition", 0.0))
    competition_penalty = float(features.get("competition_penalty", 0.0))

    data_confidence = clamp(
        0.36 * density
        + 0.18 * traffic
        + 0.15 * residential
        + 0.12 * transport
        + 0.11 * retail
        + 0.08 * saturating_count(nearby_total, 12.0)
    )
    base_score = clamp(
        0.34 * model_score
        + 0.18 * traffic
        + 0.16 * residential
        + 0.13 * retail
        + 0.10 * density
        + 0.06 * transport
        + 0.03 * office
    )
    saturation_penalty = 0.16 * competition_penalty + 0.08 * max(0.0, norm_competition - 0.55)
    uncertainty_penalty = 0.20 * (1.0 - data_confidence)
    weak_signal_penalty = 0.06 if traffic + residential + retail < 0.55 else 0.0

    return {
        "selection_score": clamp(base_score - saturation_penalty - uncertainty_penalty - weak_signal_penalty),
        "data_confidence": data_confidence,
    }


def _rank_candidates(
    cells: list[GridCell],
    feature_rows: list[dict[str, Any]],
    candidate_scores: list[dict[str, float]],
) -> dict[str, dict[str, int]]:
    ordered = sorted(
        zip(cells, feature_rows, candidate_scores),
        key=lambda item: (
            -item[2]["selection_score"],
            -item[2]["data_confidence"],
            -float(item[1].get("traffic_potential", 0.0)),
            -float(item[1].get("residential_score", 0.0)),
            float(item[1].get("competition_penalty", 0.0)),
            item[0].h3_id,
        ),
    )
    return {cell.h3_id: {"rank": rank} for rank, (cell, _row, _score) in enumerate(ordered, start=1)}


def _recommendation_for_candidate(candidate: dict[str, float], rank: int, total_cells: int) -> dict[str, str]:
    score = candidate["selection_score"]
    data_confidence = candidate["data_confidence"]
    high_priority_limit = max(3, math.ceil(total_cells * 0.02))
    promising_limit = max(10, math.ceil(total_cells * 0.18))

    if score >= 0.70 and data_confidence >= 0.30 and rank <= high_priority_limit:
        return {"code": "high_priority", "label": "Приоритетно рассмотреть"}
    if score >= 0.54 and data_confidence >= 0.22 and rank <= promising_limit:
        return {"code": "promising", "label": "Перспективная зона"}
    if score >= 0.34 and data_confidence >= 0.12:
        return {"code": "manual_review", "label": "Нужна ручная проверка"}
    return {"code": "low_priority", "label": "Низкий приоритет"}


def _top_candidates(
    cells: list[GridCell],
    model_predictions: list[float],
    candidate_scores: list[dict[str, float]],
    ranks: dict[str, dict[str, int]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    ordered = sorted(zip(cells, model_predictions, candidate_scores), key=lambda item: ranks[item[0].h3_id]["rank"])
    candidates = []
    for cell, model_score, candidate in ordered[:limit]:
        rank = ranks[cell.h3_id]["rank"]
        recommendation = _recommendation_for_candidate(candidate, rank, len(cells))
        candidates.append(
            {
                "h3_id": cell.h3_id,
                "rank": rank,
                "suitability": round(candidate["selection_score"], 3),
                "model_score": round(model_score, 3),
                "data_confidence": round(candidate["data_confidence"], 3),
                "recommendation": recommendation["code"],
                "center": {"lon": round(cell.center_lon, 7), "lat": round(cell.center_lat, 7)},
            }
        )
    return candidates


def _recommendation_counts(
    cells: list[GridCell],
    candidate_scores: list[dict[str, float]],
    ranks: dict[str, dict[str, int]],
) -> dict[str, int]:
    counts = {
        "high_priority": 0,
        "promising": 0,
        "manual_review": 0,
        "low_priority": 0,
    }
    total_cells = len(candidate_scores)
    for cell, candidate in zip(cells, candidate_scores):
        rank = ranks[cell.h3_id]["rank"]
        counts[_recommendation_for_candidate(candidate, rank, total_cells)["code"]] += 1
    return counts
