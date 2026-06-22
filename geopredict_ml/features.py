from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .business import BusinessProfile, normalize_text
from .geo import clamp, haversine_meters
from .grid import GridCell


@dataclass(frozen=True)
class PoiCategory:
    is_competitor: bool = False
    is_shop: bool = False
    is_food: bool = False
    is_public_transport: bool = False
    is_office: bool = False
    is_residential: bool = False
    is_education: bool = False


def normalize_geojson_pois(geojson: dict | None) -> list[dict[str, Any]]:
    if not geojson:
        return []
    if geojson.get("type") != "FeatureCollection":
        raise ValueError("POI data must be a GeoJSON FeatureCollection")

    pois: list[dict[str, Any]] = []
    for feature in geojson.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            continue
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            continue
        pois.append(
            {
                "lon": float(coordinates[0]),
                "lat": float(coordinates[1]),
                "tags": feature.get("properties") or {},
            }
        )
    return pois


def categorize_poi(tags: dict[str, Any], profile: BusinessProfile) -> PoiCategory:
    normalized_tags = {normalize_text(key): normalize_text(value) for key, value in tags.items()}
    values = set(normalized_tags.values())
    combined = " ".join([*normalized_tags.keys(), *normalized_tags.values()])

    competitor = any(keyword in combined for keyword in profile.competitor_keywords) or bool(
        values.intersection(profile.competitor_tag_values)
    )

    amenity = normalized_tags.get("amenity", "")
    shop = normalized_tags.get("shop", "")
    office = normalized_tags.get("office", "")
    building = normalized_tags.get("building", "")
    landuse = normalized_tags.get("landuse", "")
    highway = normalized_tags.get("highway", "")
    railway = normalized_tags.get("railway", "")
    public_transport = normalized_tags.get("public_transport", "")

    food_values = {"cafe", "restaurant", "fast_food", "food_court", "bar", "pub"}
    education_values = {"school", "university", "college", "kindergarten"}

    return PoiCategory(
        is_competitor=competitor,
        is_shop=bool(shop) and shop not in {"vacant", "no"},
        is_food=amenity in food_values,
        is_public_transport=bool(public_transport)
        or highway in {"bus_stop", "platform"}
        or railway in {"station", "subway_entrance", "tram_stop", "halt"}
        or amenity in {"bus_station"},
        is_office=bool(office) or building in {"office", "commercial"} or amenity in {"coworking_space"},
        is_residential=building in {"apartments", "residential", "house", "detached", "dormitory"} or landuse == "residential",
        is_education=amenity in education_values,
    )


def compute_cell_features(cell: GridCell, pois: list[dict[str, Any]], profile: BusinessProfile) -> dict[str, Any]:
    counts = {
        "shops": 0,
        "cafes": 0,
        "restaurants": 0,
        "competitors": 0,
        "public_transport": 0,
        "offices": 0,
        "residential": 0,
        "education": 0,
    }
    nearby_total = 0

    for poi in pois:
        distance = haversine_meters(cell.center_lon, cell.center_lat, float(poi["lon"]), float(poi["lat"]))
        if distance > profile.radius_m:
            continue
        nearby_total += 1
        category = categorize_poi(poi.get("tags", {}), profile)
        tags = {normalize_text(key): normalize_text(value) for key, value in poi.get("tags", {}).items()}

        if category.is_competitor:
            counts["competitors"] += 1
        if category.is_shop:
            counts["shops"] += 1
        if category.is_food:
            if tags.get("amenity") == "cafe":
                counts["cafes"] += 1
            else:
                counts["restaurants"] += 1
        if category.is_public_transport:
            counts["public_transport"] += 1
        if category.is_office:
            counts["offices"] += 1
        if category.is_residential:
            counts["residential"] += 1
        if category.is_education:
            counts["education"] += 1

    competition = counts["competitors"]
    norm_competition = saturating_count(competition, profile.competition_scale)
    competition_penalty = saturating_count(max(0, competition - profile.competition_soft_limit), 2.0)
    market_validation = clamp(competition / max(1, profile.validation_competitor_count))

    residential_score = saturating_count(counts["residential"], 8.0)
    transport_score = saturating_count(counts["public_transport"], 3.0)
    retail_anchor_score = saturating_count(counts["shops"] + counts["cafes"] + counts["restaurants"], 12.0)
    office_score = saturating_count(counts["offices"], 7.0)
    education_score = saturating_count(counts["education"], 4.0)
    density_score = saturating_count(nearby_total, 25.0)
    traffic_potential = clamp(
        0.28 * transport_score
        + 0.20 * retail_anchor_score
        + 0.18 * residential_score
        + 0.14 * office_score
        + 0.10 * education_score
        + 0.10 * density_score
    )

    return {
        "h3_id": cell.h3_id,
        "center_lon": cell.center_lon,
        "center_lat": cell.center_lat,
        "competition": competition,
        "norm_competition": round(norm_competition, 6),
        "competition_penalty": round(competition_penalty, 6),
        "market_validation": round(market_validation, 6),
        "traffic_potential": round(traffic_potential, 6),
        "density_score": round(density_score, 6),
        "residential_score": round(residential_score, 6),
        "transport_score": round(transport_score, 6),
        "retail_anchor_score": round(retail_anchor_score, 6),
        "office_score": round(office_score, 6),
        "education_score": round(education_score, 6),
        "nearby_poi_total": nearby_total,
        "poi_counts": counts,
    }


def saturating_count(count: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    return clamp(1.0 - math.exp(-max(0.0, count) / scale))
