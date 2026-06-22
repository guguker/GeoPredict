from __future__ import annotations

import json
from typing import Any
from urllib import parse, request

from .grid import validate_polygon_geometry


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def build_overpass_query(geometry: dict[str, Any]) -> str:
    ring = validate_polygon_geometry(geometry)
    polygon = " ".join(f"{lat} {lon}" for lon, lat in ring)
    return f"""
[out:json][timeout:60];
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


def fetch_overpass_geojson(geometry: dict[str, Any], overpass_url: str = OVERPASS_URL) -> dict[str, Any]:
    query = build_overpass_query(geometry)
    payload = parse.urlencode({"data": query}).encode("utf-8")
    http_request = request.Request(overpass_url, data=payload, headers={"User-Agent": "GeoPredict-ML/0.1"})
    with request.urlopen(http_request, timeout=90) as response:
        raw = json.loads(response.read().decode("utf-8"))
    return overpass_json_to_geojson(raw)


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
