from __future__ import annotations

import json
from typing import Any
from urllib import parse, request

from .cache import read_json_cache, stable_cache_key, write_json_cache
from .grid import validate_polygon_geometry


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def build_overpass_query(geometry: dict[str, Any], snapshot_date: str | None = None) -> str:
    ring = validate_polygon_geometry(geometry)
    polygon = " ".join(f"{lat} {lon}" for lon, lat in ring)
    date_clause = f'[date:"{snapshot_date}"]' if snapshot_date else ""
    return f"""
[out:json][timeout:60]{date_clause};
(
  nwr(poly:"{polygon}")["shop"];
  nwr(poly:"{polygon}")["amenity"];
  nwr(poly:"{polygon}")["office"];
  nwr(poly:"{polygon}")["building"];
  nwr(poly:"{polygon}")["landuse"];
  nwr(poly:"{polygon}")["leisure"];
  nwr(poly:"{polygon}")["healthcare"];
  nwr(poly:"{polygon}")["craft"];
  nwr(poly:"{polygon}")["sport"];
  nwr(poly:"{polygon}")["tourism"];
  nwr(poly:"{polygon}")["public_transport"];
  nwr(poly:"{polygon}")["highway"="bus_stop"];
  nwr(poly:"{polygon}")["railway"];
);
out center tags;
"""


def fetch_overpass_geojson(
    geometry: dict[str, Any],
    overpass_url: str = OVERPASS_URL,
    snapshot_date: str | None = None,
    cache_dir: str | None = None,
) -> dict[str, Any]:
    query = build_overpass_query(geometry, snapshot_date=snapshot_date)
    cache_key = overpass_cache_key(geometry, snapshot_date=snapshot_date)
    if cache_dir:
        cached = read_json_cache(cache_dir, cache_key)
        if cached is not None:
            return cached

    payload = parse.urlencode({"data": query}).encode("utf-8")
    http_request = request.Request(overpass_url, data=payload, headers={"User-Agent": "GeoPredict-ML/0.1"})
    with request.urlopen(http_request, timeout=90) as response:
        raw = json.loads(response.read().decode("utf-8"))
    geojson = overpass_json_to_geojson(raw)
    if cache_dir:
        write_json_cache(cache_dir, cache_key, geojson)
    return geojson


def overpass_cache_key(geometry: dict[str, Any], snapshot_date: str | None = None) -> str:
    return stable_cache_key("overpass", {"geometry": geometry, "snapshot_date": snapshot_date})


def overpass_json_to_geojson(raw: dict[str, Any]) -> dict[str, Any]:
    features = []
    for element in raw.get("elements", []):
        lon = element.get("lon")
        lat = element.get("lat")
        if lon is None or lat is None:
            center = element.get("center") or {}
            lon = center.get("lon")
            lat = center.get("lat")
        if lon is None or lat is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "properties": element.get("tags", {}) | {"osm_id": element.get("id"), "osm_type": element.get("type")},
            }
        )
    return {"type": "FeatureCollection", "features": features}
