from __future__ import annotations

import argparse
import json
from pathlib import Path

from geopredict_ml.osm import fetch_overpass_geojson
from geopredict_ml.pipeline import analyze_request


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a GeoJSON polygon and print GeoPredict FeatureCollection.")
    parser.add_argument("--request", required=True, help="Path to request JSON.")
    parser.add_argument("--pois", help="Optional local POI GeoJSON. If omitted, --live-osm may fetch Overpass data.")
    parser.add_argument("--model", help="Optional trained model artifact path.")
    parser.add_argument("--live-osm", action="store_true", help="Fetch POIs from OpenStreetMap Overpass.")
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()

    payload = json.loads(Path(args.request).read_text(encoding="utf-8"))
    if args.pois:
        pois = json.loads(Path(args.pois).read_text(encoding="utf-8"))
    elif args.live_osm:
        pois = fetch_overpass_geojson(payload["geometry"])
    else:
        pois = None

    result = analyze_request(payload, pois_geojson=pois, model_path=args.model)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
