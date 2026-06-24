from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math

from .geo import (
    meters_to_lat_degrees,
    meters_to_lon_degrees,
    normalize_ring,
    point_in_polygon,
    polygon_area_square_meters,
    polygon_bbox,
    polygon_centroid,
    regular_hexagon,
)


@dataclass(frozen=True)
class GridCell:
    h3_id: str
    center_lon: float
    center_lat: float
    geometry: dict
    backend: str = "fallback_hex"


H3_APPROX_RADIUS_M = {
    7: 1_220.0,
    8: 460.0,
    9: 175.0,
    10: 66.0,
}

H3_APPROX_AREA_KM2 = {
    7: 5.16,
    8: 0.737,
    9: 0.105,
    10: 0.015,
}


class AnalysisAreaTooLargeError(ValueError):
    def __init__(
        self,
        estimated_cells: int,
        max_cells: int,
        resolution: int | None = None,
    ) -> None:
        self.estimated_cells = estimated_cells
        self.max_cells = max_cells
        self.resolution = resolution
        self.suggested_resolution = (
            suggest_h3_resolution(estimated_cells, max_cells, resolution)
            if resolution is not None
            else None
        )
        super().__init__(
            f"Selected area requires approximately {estimated_cells} cells; "
            f"the synchronous limit is {max_cells}. Draw a smaller area or use a lower H3 resolution."
        )


def validate_polygon_geometry(geometry: dict) -> list[list[float]]:
    if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
        raise ValueError("geometry must be a GeoJSON Polygon")
    coordinates = geometry.get("coordinates")
    if not coordinates or not isinstance(coordinates, list):
        raise ValueError("geometry.coordinates must contain an outer ring")
    return normalize_ring(coordinates[0])


def polygon_to_grid_cells(geometry: dict, resolution: int = 9, max_cells: int = 1_000) -> list[GridCell]:
    ring = validate_analysis_area(geometry, resolution=resolution, max_cells=max_cells)

    h3_cells = _polygon_to_h3_cells_if_available(ring, resolution)
    if h3_cells:
        if len(h3_cells) > max_cells:
            raise AnalysisAreaTooLargeError(len(h3_cells), max_cells, resolution)
        return h3_cells

    return _polygon_to_fallback_hex_cells(ring, resolution, max_cells)


def validate_analysis_area(
    geometry: dict,
    resolution: int = 9,
    max_cells: int = 1_000,
) -> list[list[float]]:
    ring = validate_polygon_geometry(geometry)
    estimated_cells = _estimate_cell_count(ring, resolution)
    if estimated_cells > max_cells:
        raise AnalysisAreaTooLargeError(estimated_cells, max_cells, resolution)
    return ring


def suggest_h3_resolution(
    estimated_cells: int,
    max_cells: int,
    resolution: int,
) -> int | None:
    current_area = H3_APPROX_AREA_KM2.get(resolution)
    if current_area is None:
        return None

    estimated_area_km2 = estimated_cells * current_area
    for candidate in range(resolution - 1, min(H3_APPROX_AREA_KM2) - 1, -1):
        candidate_cells = math.ceil(estimated_area_km2 / H3_APPROX_AREA_KM2[candidate])
        if candidate_cells <= max_cells:
            return candidate
    return None


def _polygon_to_h3_cells_if_available(ring: list[list[float]], resolution: int) -> list[GridCell]:
    try:
        import h3  # type: ignore
    except Exception:
        return []

    try:
        outer_ring = ring[:-1] if ring[0] == ring[-1] else ring
        lat_lng_ring = [(lat, lon) for lon, lat in outer_ring]
        if hasattr(h3, "LatLngPoly") and hasattr(h3, "polygon_to_cells"):
            polygon = h3.LatLngPoly(lat_lng_ring)
            raw_cells = list(h3.polygon_to_cells(polygon, resolution))
        elif hasattr(h3, "polyfill"):
            raw_cells = list(h3.polyfill({"type": "Polygon", "coordinates": [ring]}, resolution, geo_json_conformant=True))
        else:
            return []

        cells: list[GridCell] = []
        for cell_id in raw_cells:
            center_lat, center_lon = _h3_cell_center(h3, cell_id)
            boundary = _h3_cell_boundary(h3, cell_id)
            cells.append(
                GridCell(
                    h3_id=str(cell_id),
                    center_lon=center_lon,
                    center_lat=center_lat,
                    geometry={"type": "Polygon", "coordinates": [boundary]},
                    backend="h3",
                )
            )
        return cells
    except Exception:
        return []


def _h3_cell_center(h3_module: object, cell_id: str) -> tuple[float, float]:
    if hasattr(h3_module, "cell_to_latlng"):
        return tuple(h3_module.cell_to_latlng(cell_id))  # type: ignore[return-value]
    return tuple(h3_module.h3_to_geo(cell_id))  # type: ignore[attr-defined, return-value]


def _h3_cell_boundary(h3_module: object, cell_id: str) -> list[list[float]]:
    if hasattr(h3_module, "cell_to_boundary"):
        boundary = h3_module.cell_to_boundary(cell_id)  # type: ignore[attr-defined]
    else:
        boundary = h3_module.h3_to_geo_boundary(cell_id)  # type: ignore[attr-defined]
    coords = [[float(lon), float(lat)] for lat, lon in boundary]
    coords.append(coords[0])
    return coords


def _polygon_to_fallback_hex_cells(ring: list[list[float]], resolution: int, max_cells: int) -> list[GridCell]:
    min_lon, min_lat, max_lon, max_lat = polygon_bbox(ring)
    center_lon, center_lat = polygon_centroid(ring)
    radius_m = H3_APPROX_RADIUS_M.get(resolution, H3_APPROX_RADIUS_M[9])
    x_spacing_m = math.sqrt(3.0) * radius_m
    y_spacing_m = 1.5 * radius_m

    lat_step = meters_to_lat_degrees(y_spacing_m)
    lon_step = meters_to_lon_degrees(x_spacing_m, center_lat)
    cells: list[GridCell] = []

    row = 0
    lat = min_lat - lat_step
    while lat <= max_lat + lat_step and len(cells) <= max_cells:
        offset = lon_step / 2.0 if row % 2 else 0.0
        lon = min_lon - lon_step + offset
        while lon <= max_lon + lon_step and len(cells) <= max_cells:
            if point_in_polygon(lon, lat, ring):
                cells.append(_fallback_cell(lon, lat, radius_m, resolution))
            lon += lon_step
        lat += lat_step
        row += 1

    if len(cells) > max_cells:
        raise AnalysisAreaTooLargeError(len(cells), max_cells, resolution)
    if not cells:
        cells.append(_fallback_cell(center_lon, center_lat, radius_m, resolution))
    return cells


def _estimate_cell_count(ring: list[list[float]], resolution: int) -> int:
    area_km2 = polygon_area_square_meters(ring) / 1_000_000.0
    cell_area_km2 = H3_APPROX_AREA_KM2.get(resolution, H3_APPROX_AREA_KM2[9])
    return max(1, math.ceil(area_km2 / cell_area_km2))


def _fallback_cell(lon: float, lat: float, radius_m: float, resolution: int) -> GridCell:
    key = f"{resolution}:{lon:.7f}:{lat:.7f}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:13]
    return GridCell(
        h3_id=f"h3fallback_{resolution}_{digest}",
        center_lon=lon,
        center_lat=lat,
        geometry=regular_hexagon(lon, lat, radius_m),
    )
