from __future__ import annotations

from typing import Any

from .business import BusinessProfile
from .features import categorize_poi, normalize_geojson_pois
from .geo import clamp


def business_snapshot_diff(
    before_geojson: dict[str, Any],
    after_geojson: dict[str, Any],
    profile: BusinessProfile,
) -> dict[str, Any]:
    before = _business_poi_index(before_geojson, profile)
    after = _business_poi_index(after_geojson, profile)

    before_ids = set(before)
    after_ids = set(after)
    appeared_ids = sorted(after_ids - before_ids)
    disappeared_ids = sorted(before_ids - after_ids)
    stayed_ids = sorted(before_ids & after_ids)

    return {
        "business_type": profile.business_type,
        "profile_title": profile.title,
        "summary": {
            "before_count": len(before),
            "after_count": len(after),
            "appeared_count": len(appeared_ids),
            "disappeared_count": len(disappeared_ids),
            "stayed_count": len(stayed_ids),
            "survival_rate": round(clamp(len(stayed_ids) / max(1, len(before))), 6),
        },
        "appeared": [after[poi_id] | {"event": "appeared"} for poi_id in appeared_ids],
        "disappeared": [before[poi_id] | {"event": "disappeared"} for poi_id in disappeared_ids],
        "stayed": [after[poi_id] | {"event": "stayed"} for poi_id in stayed_ids],
    }


def _business_poi_index(geojson: dict[str, Any], profile: BusinessProfile) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for poi in normalize_geojson_pois(geojson):
        tags = poi.get("tags", {})
        if not categorize_poi(tags, profile).is_competitor:
            continue
        poi_id = poi_identity(poi)
        indexed[poi_id] = {
            "poi_id": poi_id,
            "lat": round(float(poi["lat"]), 7),
            "lon": round(float(poi["lon"]), 7),
            "name": str(tags.get("name") or tags.get("brand") or ""),
            "tags": tags,
        }
    return indexed


def poi_identity(poi: dict[str, Any]) -> str:
    tags = poi.get("tags", {})
    osm_id = tags.get("osm_id")
    osm_type = tags.get("osm_type", "node")
    if osm_id is not None:
        return f"osm:{osm_type}:{osm_id}"

    name = str(tags.get("name") or tags.get("brand") or "").strip().lower()
    category = str(tags.get("shop") or tags.get("amenity") or tags.get("craft") or tags.get("tourism") or "")
    lon = round(float(poi["lon"]), 5)
    lat = round(float(poi["lat"]), 5)
    return f"fallback:{name}:{category}:{lon}:{lat}"
