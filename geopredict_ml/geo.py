from __future__ import annotations

import math
from typing import Iterable


EARTH_RADIUS_M = 6_371_000.0


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def haversine_meters(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def polygon_bbox(ring: list[list[float]]) -> tuple[float, float, float, float]:
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return min(lons), min(lats), max(lons), max(lats)


def polygon_centroid(ring: list[list[float]]) -> tuple[float, float]:
    usable = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    lon = sum(point[0] for point in usable) / len(usable)
    lat = sum(point[1] for point in usable) / len(usable)
    return lon, lat


def point_in_polygon(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        intersects = (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def meters_to_lat_degrees(meters: float) -> float:
    return meters / 111_320.0


def meters_to_lon_degrees(meters: float, lat: float) -> float:
    return meters / (111_320.0 * max(0.2, math.cos(math.radians(lat))))


def regular_hexagon(lon: float, lat: float, radius_m: float) -> dict:
    coords: list[list[float]] = []
    for i in range(6):
        angle = math.radians(60 * i + 30)
        dx = math.cos(angle) * radius_m
        dy = math.sin(angle) * radius_m
        coords.append([lon + meters_to_lon_degrees(dx, lat), lat + meters_to_lat_degrees(dy)])
    coords.append(coords[0])
    return {"type": "Polygon", "coordinates": [coords]}


def normalize_ring(coords: Iterable[Iterable[float]]) -> list[list[float]]:
    ring = [[float(point[0]), float(point[1])] for point in coords]
    if len(ring) < 4:
        raise ValueError("Polygon outer ring must contain at least four points")
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring
