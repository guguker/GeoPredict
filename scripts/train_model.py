from __future__ import annotations

import argparse
import json
from pathlib import Path

from geopredict_ml.business import get_business_profile
from geopredict_ml.features import compute_cell_features, normalize_geojson_pois
from geopredict_ml.grid import polygon_to_grid_cells
from geopredict_ml.model_registry import model_artifact_path
from geopredict_ml.model import GradientBoostingRegressorLite
from geopredict_ml.target import proxy_location_success, reference_training_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Train GeoPredict proxy-success ML model.")
    parser.add_argument("--business-type", default="pickup_point", help="Business profile to train.")
    parser.add_argument("--request", help="Optional request JSON for area-specific feature rows.")
    parser.add_argument("--pois", help="Optional POI GeoJSON for area-specific feature rows.")
    parser.add_argument("--output", help="Output model artifact path. Defaults to the registry path for business type.")
    args = parser.parse_args()

    profile = get_business_profile(args.business_type)
    output = args.output or str(model_artifact_path(profile))

    if args.request and args.pois:
        payload = json.loads(Path(args.request).read_text(encoding="utf-8"))
        pois = normalize_geojson_pois(json.loads(Path(args.pois).read_text(encoding="utf-8")))
        cells = polygon_to_grid_cells(payload["geometry"], int(payload.get("h3_resolution", 9)))
        rows = [compute_cell_features(cell, pois, profile) for cell in cells]
        targets = [proxy_location_success(row, profile) for row in rows]
        if len(rows) < 20:
            reference_rows, reference_targets = reference_training_rows(profile)
            rows.extend(reference_rows)
            targets.extend(reference_targets)
    else:
        rows, targets = reference_training_rows(profile)

    model = GradientBoostingRegressorLite().fit(rows, targets)
    model.business_type = profile.business_type
    model.profile_title = profile.title
    model.save(output)
    print(f"Saved {model.model_type} {model.model_version} to {output}")
    print(f"Business type: {profile.business_type}")
    print(f"Training rows: {len(rows)}")


if __name__ == "__main__":
    main()
