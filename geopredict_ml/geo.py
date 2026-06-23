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


def polygon_area_square_meters(ring: list[list[float]]) -> float:
    usable = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    if len(usable) < 3:
        return 0.0

    reference_lat = sum(point[1] for point in usable) / len(usable)
    unwrapped_lons = _unwrap_longitudes([point[0] for point in usable])
    scale_x = 111_320.0 * max(0.01, math.cos(math.radians(reference_lat)))
    scale_y = 111_320.0
    points = [(lon * scale_x, lat * scale_y) for lon, (_, lat) in zip(unwrapped_lons, usable)]

    area = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


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
    ring: list[list[float]] = []
    for index, point in enumerate(coords):
        try:
            lon = float(point[0])
            lat = float(point[1])
        except (IndexError, TypeError, ValueError) as exc:
            raise ValueError(f"Polygon point {index} must contain numeric longitude and latitude") from exc
        if not math.isfinite(lon) or not math.isfinite(lat):
            raise ValueError(f"Polygon point {index} contains a non-finite coordinate")
        if not -180.0 <= lon <= 180.0 or not -90.0 <= lat <= 90.0:
            raise ValueError(f"Polygon point {index} is outside valid longitude/latitude bounds")
        ring.append([lon, lat])

    if len(ring) < 4:
        raise ValueError("Polygon outer ring must contain at least four points")
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    if len({(point[0], point[1]) for point in ring[:-1]}) < 3:
        raise ValueError("Polygon must contain at least three distinct vertices")
    if polygon_area_square_meters(ring) < 1.0:
        raise ValueError("Polygon area is too small or degenerate")
    if _ring_self_intersects(ring):
        raise ValueError("Polygon must not self-intersect")
    return ring


def simplify_ring(ring: list[list[float]], max_vertices: int = 24) -> list[list[float]]:
    usable = ring[:-1] if ring[0] == ring[-1] else ring
    if len(usable) <= max_vertices:
        return [*usable, usable[0]]

    indexes = {
        min(len(usable) - 1, round(index * len(usable) / max_vertices))
        for index in range(max_vertices)
    }
    simplified = [usable[index] for index in sorted(indexes)]
    return [*simplified, simplified[0]]


def _unwrap_longitudes(longitudes: list[float]) -> list[float]:
    if not longitudes:
        return []
    result = [longitudes[0]]
    for longitude in longitudes[1:]:
        adjusted = longitude
        while adjusted - result[-1] > 180.0:
            adjusted -= 360.0
        while adjusted - result[-1] < -180.0:
            adjusted += 360.0
        result.append(adjusted)
    return result


def _ring_self_intersects(ring: list[list[float]]) -> bool:
    segment_count = len(ring) - 1
    for first in range(segment_count):
        a1, a2 = ring[first], ring[first + 1]
        for second in range(first + 1, segment_count):
            if abs(first - second) <= 1:
                continue
            if first == 0 and second == segment_count - 1:
                continue
            b1, b2 = ring[second], ring[second + 1]
            if _segments_intersect(a1, a2, b1, b2):
                return True
    return False


def _segments_intersect(
    a1: list[float],
    a2: list[float],
    b1: list[float],
    b2: list[float],
) -> bool:
    def orientation(p: list[float], q: list[float], r: list[float]) -> float:
        return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)
