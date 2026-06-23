from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Callable
from urllib import error, parse, request

from .geo import simplify_ring
from .grid import validate_polygon_geometry


OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
OVERPASS_URL = OVERPASS_URLS[0]
DEFAULT_CACHE_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class OverpassFetchResult:
    geojson: dict[str, Any]
    source: str
    endpoint: str | None = None
    warnings: tuple[str, ...] = ()


def build_overpass_query(geometry: dict[str, Any]) -> str:
    ring = simplify_ring(validate_polygon_geometry(geometry), max_vertices=16)
    polygon = " ".join(f"{lat:.7f} {lon:.7f}" for lon, lat in ring)
    return f"""
[out:json][timeout:30];
(
  nwr(poly:"{polygon}")["shop"];
  nwr(poly:"{polygon}")["amenity"];
  nwr(poly:"{polygon}")["office"];
  nwr(poly:"{polygon}")[~"^(craft|tourism|leisure|healthcare|sport|public_transport)$"~"."];
  nwr(poly:"{polygon}")["building"~"^(apartments|residential|house|detached|dormitory|office|commercial)$"];
  nwr(poly:"{polygon}")["landuse"="residential"];
  nwr(poly:"{polygon}")["highway"="bus_stop"];
  nwr(poly:"{polygon}")["railway"~"^(station|subway_entrance|tram_stop|halt)$"];
);
out center tags;
"""


def fetch_overpass_result(
    geometry: dict[str, Any],
    overpass_urls: tuple[str, ...] | None = None,
    cache_dir: str | Path | None = None,
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    timeout_seconds: int = 35,
    opener: Callable[..., Any] | None = None,
) -> OverpassFetchResult:
    query = build_overpass_query(geometry)
    resolved_cache_dir = cache_dir or os.getenv("GEOPREDICT_OSM_CACHE_DIR")
    cached = _read_cache(query, resolved_cache_dir, cache_ttl_seconds, allow_stale=False)
    if cached:
        return OverpassFetchResult(cached, source="osm_cache")

    endpoints = overpass_urls or OVERPASS_URLS
    open_url = opener or request.urlopen
    failures: list[str] = []

    for endpoint in endpoints:
        payload = parse.urlencode({"data": query}).encode("utf-8")
        http_request = request.Request(
            endpoint,
            data=payload,
            headers={"User-Agent": "GeoPredict-ML/0.2"},
        )
        try:
            with open_url(http_request, timeout=timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
            geojson = overpass_json_to_geojson(raw)
            _write_cache(query, geojson, resolved_cache_dir)
            return OverpassFetchResult(geojson, source="osm_live", endpoint=endpoint)
        except (error.HTTPError, error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"{endpoint}: {_format_fetch_error(exc)}")

    stale = _read_cache(query, resolved_cache_dir, cache_ttl_seconds, allow_stale=True)
    if stale:
        return OverpassFetchResult(
            stale,
            source="osm_cache_stale",
            warnings=("Live OSM is unavailable; an expired cached snapshot was used.",),
        )

    raise RuntimeError("All Overpass endpoints failed: " + " | ".join(failures))


def fetch_overpass_geojson(
    geometry: dict[str, Any],
    overpass_url: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    urls = (overpass_url,) if overpass_url else None
    return fetch_overpass_result(geometry, overpass_urls=urls, **kwargs).geojson


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
                "properties": element.get("tags", {})
                | {"osm_id": element.get("id"), "osm_type": element.get("type")},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _cache_path(query: str, cache_dir: str | Path | None) -> Path | None:
    if not cache_dir:
        return None
    key = hashlib.sha256(query.encode("utf-8")).hexdigest()
    return Path(cache_dir) / f"{key}.json"


def _read_cache(
    query: str,
    cache_dir: str | Path | None,
    cache_ttl_seconds: int,
    allow_stale: bool,
) -> dict[str, Any] | None:
    path = _cache_path(query, cache_dir)
    if not path or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        age = time.time() - float(payload["fetched_at"])
        if age > cache_ttl_seconds and not allow_stale:
            return None
        geojson = payload["geojson"]
        if geojson.get("type") != "FeatureCollection":
            return None
        return geojson
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _write_cache(query: str, geojson: dict[str, Any], cache_dir: str | Path | None) -> None:
    path = _cache_path(query, cache_dir)
    if not path:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"fetched_at": time.time(), "geojson": geojson}, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError:
        return


def _format_fetch_error(exc: Exception) -> str:
    status = getattr(exc, "code", None)
    reason = getattr(exc, "reason", None)
    if status and reason:
        return f"HTTP {status}: {reason}"
    return str(exc) or exc.__class__.__name__
