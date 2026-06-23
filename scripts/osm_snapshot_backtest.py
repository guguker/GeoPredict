from __future__ import annotations

import argparse
import json
from pathlib import Path

from geopredict_ml.business import get_business_profile
from geopredict_ml.osm_history import business_snapshot_diff


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two OSM POI snapshots for one business profile.")
    parser.add_argument("--before", required=True, help="Older OSM POI GeoJSON snapshot.")
    parser.add_argument("--after", required=True, help="Newer OSM POI GeoJSON snapshot.")
    parser.add_argument("--business-type", default="pickup_point", help="Business profile or alias.")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()

    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    profile = get_business_profile(args.business_type)
    report = business_snapshot_diff(before, after, profile)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
