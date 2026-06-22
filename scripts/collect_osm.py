from __future__ import annotations

import argparse
import json
from pathlib import Path

from geopredict_ml.osm import fetch_overpass_geojson


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect OpenStreetMap POIs for a request polygon via Overpass.")
    parser.add_argument("--request", required=True, help="Path to request JSON containing geometry.")
    parser.add_argument("--output", required=True, help="Output POI GeoJSON path.")
    args = parser.parse_args()

    payload = json.loads(Path(args.request).read_text(encoding="utf-8"))
    geojson = fetch_overpass_geojson(payload["geometry"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(geojson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(geojson['features'])} POIs to {output}")


if __name__ == "__main__":
    main()
