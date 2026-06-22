from __future__ import annotations

from pathlib import Path
from typing import Any

from .business import get_business_profile
from .explain import build_explanation
from .features import compute_cell_features, normalize_geojson_pois
from .grid import polygon_to_grid_cells, validate_polygon_geometry
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

    features = []
    for cell, row, score in zip(cells, feature_rows, predictions):
        properties = {
            "h3_id": cell.h3_id,
            "suitability": round(score, 3),
            "success_probability": round(score, 3),
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
        },
    }


def _load_or_train_model(profile: Any, model_path: str | Path | None) -> GradientBoostingRegressorLite:
    if model_path and Path(model_path).exists():
        return GradientBoostingRegressorLite.load(model_path)
    return train_reference_model(profile)
