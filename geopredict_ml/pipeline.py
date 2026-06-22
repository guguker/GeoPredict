from __future__ import annotations

from pathlib import Path
from typing import Any

from .business import get_business_profile
from .explain import build_explanation
from .features import compute_cell_features, normalize_geojson_pois
from .grid import GridCell, polygon_to_grid_cells, validate_polygon_geometry
from .model import GradientBoostingRegressorLite, train_reference_model


def analyze_request(
    request_payload: dict[str, Any],
    pois_geojson: dict | None = None,
    model_path: str | Path | None = None,
    max_cells: int = 1_000,
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
    feature_rows = [compute_cell_features(cell, pois, profile) for cell in cells]
    model = _load_or_train_model(profile, model_path)
    predictions = model.predict(feature_rows)
    ranked_predictions = _rank_predictions(cells, predictions)

    features = []
    for cell, row, score in zip(cells, feature_rows, predictions):
        rank_info = ranked_predictions[cell.h3_id]
        recommendation = _recommendation_for_score(score)
        properties = {
            "h3_id": cell.h3_id,
            "rank": rank_info["rank"],
            "suitability": round(score, 3),
            "success_probability": round(score, 3),
            "recommendation": recommendation["code"],
            "recommendation_label": recommendation["label"],
            "competition": row["competition"],
            "norm_competition": round(float(row["norm_competition"]), 3),
            "competition_penalty": round(float(row["competition_penalty"]), 3),
            "market_validation": round(float(row["market_validation"]), 3),
            "traffic_potential": round(float(row["traffic_potential"]), 3),
            "density_score": round(float(row["density_score"]), 3),
            "poi_counts": row["poi_counts"],
            "explanation": build_explanation(row, score, profile),
        }
        features.append({"type": "Feature", "geometry": cell.geometry, "properties": properties})

    avg_suitability = round(sum(predictions) / len(predictions), 3) if predictions else 0.0
    grid_backend = cells[0].backend if cells else "unknown"
    top_candidates = _top_candidates(cells, predictions, ranked_predictions)
    recommendation_counts = _recommendation_counts(predictions)

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_hexagons": len(features),
            "h3_resolution": resolution,
            "avg_suitability": avg_suitability,
            "business_type": profile.business_type,
            "data_sources": ["osm"] if pois_geojson else [],
            "model_active": True,
            "model_type": model.model_type,
            "model_version": model.model_version,
            "target_type": "proxy_location_success",
            "grid_backend": grid_backend,
            "top_candidates": top_candidates,
            "recommendation_counts": recommendation_counts,
        },
    }


def _load_or_train_model(profile: Any, model_path: str | Path | None) -> GradientBoostingRegressorLite:
    if model_path and Path(model_path).exists():
        return GradientBoostingRegressorLite.load(model_path)
    return train_reference_model(profile)


def _rank_predictions(cells: list[GridCell], predictions: list[float]) -> dict[str, dict[str, int]]:
    ordered = sorted(zip(cells, predictions), key=lambda item: (-item[1], item[0].h3_id))
    return {cell.h3_id: {"rank": rank} for rank, (cell, _score) in enumerate(ordered, start=1)}


def _recommendation_for_score(score: float) -> dict[str, str]:
    if score >= 0.75:
        return {"code": "high_priority", "label": "Приоритетно рассмотреть"}
    if score >= 0.58:
        return {"code": "promising", "label": "Перспективная зона"}
    if score >= 0.42:
        return {"code": "manual_review", "label": "Нужна ручная проверка"}
    return {"code": "low_priority", "label": "Низкий приоритет"}


def _top_candidates(
    cells: list[GridCell],
    predictions: list[float],
    ranks: dict[str, dict[str, int]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    ordered = sorted(zip(cells, predictions), key=lambda item: ranks[item[0].h3_id]["rank"])
    candidates = []
    for cell, score in ordered[:limit]:
        recommendation = _recommendation_for_score(score)
        candidates.append(
            {
                "h3_id": cell.h3_id,
                "rank": ranks[cell.h3_id]["rank"],
                "suitability": round(score, 3),
                "recommendation": recommendation["code"],
                "center": {"lon": round(cell.center_lon, 7), "lat": round(cell.center_lat, 7)},
            }
        )
    return candidates


def _recommendation_counts(predictions: list[float]) -> dict[str, int]:
    counts = {
        "high_priority": 0,
        "promising": 0,
        "manual_review": 0,
        "low_priority": 0,
    }
    for score in predictions:
        counts[_recommendation_for_score(score)["code"]] += 1
    return counts
