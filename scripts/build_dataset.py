from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from geopredict_ml.business import get_business_profile
from geopredict_ml.features import compute_cell_features, normalize_geojson_pois
from geopredict_ml.grid import polygon_to_grid_cells
from geopredict_ml.target import MODEL_FEATURES, proxy_location_success


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an H3 feature dataset for ML training and review.")
    parser.add_argument("--request", required=True, help="Path to request JSON.")
    parser.add_argument("--pois", required=True, help="Path to POI GeoJSON.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    args = parser.parse_args()

    payload = json.loads(Path(args.request).read_text(encoding="utf-8"))
    profile = get_business_profile(payload["business_type"])
    pois = normalize_geojson_pois(json.loads(Path(args.pois).read_text(encoding="utf-8")))
    cells = polygon_to_grid_cells(payload["geometry"], int(payload.get("h3_resolution", 9)))

    rows = []
    for cell in cells:
        features = compute_cell_features(cell, pois, profile)
        poi_counts = features.pop("poi_counts")
        row = {
            "h3_id": cell.h3_id,
            "business_type": profile.business_type,
            "center_lon": round(cell.center_lon, 7),
            "center_lat": round(cell.center_lat, 7),
        }
        for name in MODEL_FEATURES:
            row[name] = features.get(name, 0.0)
        row.update({f"poi_{key}": value for key, value in poi_counts.items()})
        row["target_success"] = round(proxy_location_success(features | {"poi_counts": poi_counts}, profile), 6)
        rows.append(row)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(f"Saved {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
