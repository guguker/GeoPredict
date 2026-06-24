from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Literal

from geopredict_ml.business import (
    UnsupportedBusinessTypeError,
    business_type_catalog,
    custom_business_candidate,
    resolve_business_profile,
    suggest_business_profiles,
    supported_business_types,
)
from geopredict_ml.geo import polygon_bbox
from geopredict_ml.grid import AnalysisAreaTooLargeError, validate_analysis_area, validate_polygon_geometry
from geopredict_ml.osm import OverpassFetchResult, fetch_overpass_result
from geopredict_ml.pipeline import analyze_request


try:
    from fastapi import Body, FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - optional web dependency
    Body = None
    CORSMiddleware = None
    BaseModel = object
    FastAPI = None
    Field = None
    HTTPException = Exception
    Query = None


REQUEST_EXAMPLE = {
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [37.6173, 55.7558],
                [37.6273, 55.7558],
                [37.6273, 55.7658],
                [37.6173, 55.7658],
                [37.6173, 55.7558],
            ]
        ],
    },
    "business_type": "pickup_point",
    "h3_resolution": 9,
    "use_live_osm": True,
    "allow_custom_business": True,
}

RESPONSE_EXAMPLE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[37.6173, 55.7558], [37.6176, 55.7559], [37.6173, 55.7560]]]},
            "properties": {
                "h3_id": "891f1d489ffffff",
                "rank": 1,
                "top_percentile": 0.01,
                "suitability": 0.742,
                "success_probability": 0.742,
                "model_score": 0.812,
                "selection_score": 0.742,
                "data_confidence": 0.781,
                "recommendation": "high_priority",
                "recommendation_label": "Приоритетно рассмотреть",
                "competition": 3,
                "norm_competition": 0.428,
                "competition_penalty": 0.0,
                "market_validation": 1.0,
                "traffic_potential": 0.691,
                "density_score": 0.638,
                "poi_counts": {
                    "shops": 12,
                    "cafes": 5,
                    "restaurants": 8,
                    "competitors": 3,
                    "public_transport": 4,
                    "offices": 6,
                    "residential": 15,
                    "education": 2,
                },
                "explanation": ["Перспективная локация", "Конкуренция есть, но зона не выглядит перенасыщенной"],
            },
        }
    ],
    "metadata": {
        "total_hexagons": 42,
        "h3_resolution": 9,
        "avg_suitability": 0.654,
        "business_type": "pickup_point",
        "business_title": "Пункт выдачи заказов",
        "business_category": "marketplace_logistics",
        "business_query": None,
        "is_custom_business": False,
        "data_sources": ["osm"],
        "data_status": "live",
        "data_warnings": [],
        "poi_count": 1284,
        "model_active": True,
        "model_type": "GradientBoostingRegressorLite",
        "model_version": "geo-boost-lite-v1",
        "model_source": "registered_artifact",
        "model_artifact_path": "models/geopredict_pvz_v1.pkl",
        "target_type": "proxy_location_success",
        "grid_backend": "h3",
        "top_candidates": [
            {
                "h3_id": "891f1d489ffffff",
                "rank": 1,
                "suitability": 0.742,
                "model_score": 0.812,
                "data_confidence": 0.781,
                "recommendation": "high_priority",
                "center": {"lon": 37.6173, "lat": 55.7558},
            }
        ],
        "recommendation_counts": {
            "high_priority": 4,
            "promising": 21,
            "manual_review": 14,
            "low_priority": 3,
        },
        "selection_policy": "strict_v2_rank_confidence_saturation",
    },
}

BUSINESS_TYPES_EXAMPLE = {
    "total": 20,
    "business_types": [
        {
            "business_type": "pickup_point",
            "title": "Пункт выдачи заказов",
            "category": "marketplace_logistics",
            "aliases": ["pickup_point", "pvz", "пвз", "ozon", "wildberries"],
            "examples": ["Ozon", "Wildberries", "Яндекс Маркет", "СДЭК", "Boxberry"],
            "radius_m": 500,
        },
        {
            "business_type": "coffee_shop",
            "title": "Кофейня",
            "category": "food_service",
            "aliases": ["coffee_shop", "coffee", "cafe", "кофейня", "кофе"],
            "examples": ["кофейня у дома", "кофе с собой", "specialty coffee"],
            "radius_m": 350,
        },
    ],
    "custom_candidate": {
        "business_type": "custom_osm",
        "title": "Пользовательский бизнес: кофе",
        "category": "custom_osm_search",
        "source_query": "кофе",
        "is_custom": True,
    },
}

DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
DEFAULT_OSM_CACHE_DIR = "/tmp/geopredict-osm-cache"
SAMPLE_REQUEST_PATH = Path(__file__).resolve().parents[1] / "data" / "sample" / "request_pvz.json"
SAMPLE_POIS_PATH = Path(__file__).resolve().parents[1] / "data" / "sample" / "osm_pois_pvz_sample.geojson"


@dataclass(frozen=True)
class PoiSource:
    geojson: dict
    source: str
    warnings: tuple[str, ...] = ()
    fetched_at: float | None = None


class DataSourceUnavailableError(RuntimeError):
    pass


class MockDataUnavailableError(ValueError):
    pass


def get_cors_origins() -> list[str]:
    raw_origins = os.getenv("GEOPREDICT_CORS_ORIGINS")
    if not raw_origins:
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def resolve_poi_source(
    payload: dict,
    fetcher=fetch_overpass_result,
    mock_loader=None,
) -> PoiSource:
    data_mode = str(payload.get("data_mode") or "live")
    if data_mode == "mock":
        loader = mock_loader or _load_mock_pois
        return PoiSource(
            geojson=loader(payload),
            source="mock_sample",
            warnings=(
                "Используются демонстрационные sample-данные ПВЗ. "
                "Результат нельзя считать оценкой реального рынка.",
            ),
        )
    if data_mode != "live":
        raise ValueError("data_mode must be either 'live' or 'mock'")
    if payload.get("use_live_osm") is False:
        raise ValueError("use_live_osm=false is no longer implicit fallback; use data_mode='mock' explicitly")

    try:
        if fetcher is fetch_overpass_result:
            fetched = fetcher(
                payload["geometry"],
                cache_dir=os.getenv("GEOPREDICT_OSM_CACHE_DIR", DEFAULT_OSM_CACHE_DIR),
            )
        else:
            fetched = fetcher(payload["geometry"])
        if isinstance(fetched, OverpassFetchResult):
            return PoiSource(fetched.geojson, fetched.source, fetched.warnings, fetched.fetched_at)
        return PoiSource(fetched, "osm_live")
    except Exception as exc:
        raise DataSourceUnavailableError(
            "Не удалось получить данные OpenStreetMap/Overpass. "
            f"Повторите запрос позже ({_format_dependency_error(exc)})."
        ) from exc


def _format_dependency_error(exc: Exception) -> str:
    status = getattr(exc, "code", None)
    reason = getattr(exc, "reason", None)
    if status and reason:
        return f"HTTP {status}: {reason}"
    return str(exc) or exc.__class__.__name__


def _load_mock_pois(payload: dict) -> dict:
    requested_type = payload.get("business_query") if payload.get("business_type") == "custom_osm" else payload.get("business_type")
    profile = resolve_business_profile(str(requested_type or ""), allow_custom=True)
    if profile.business_type != "pickup_point":
        raise MockDataUnavailableError("Mock/sample data is available only for the pickup_point demo")

    requested_ring = validate_polygon_geometry(payload.get("geometry"))
    sample_request = json.loads(SAMPLE_REQUEST_PATH.read_text(encoding="utf-8"))
    sample_ring = validate_polygon_geometry(sample_request["geometry"])
    if not _bboxes_intersect(polygon_bbox(requested_ring), polygon_bbox(sample_ring)):
        raise MockDataUnavailableError(
            "Mock/sample data covers only the bundled Moscow demo polygon. "
            "Use live data for another territory."
        )
    return json.loads(SAMPLE_POIS_PATH.read_text(encoding="utf-8"))


def _bboxes_intersect(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    return not (
        first[2] < second[0]
        or first[0] > second[2]
        or first[3] < second[1]
        or first[1] > second[3]
    )


if FastAPI:
    class AnalyzeRequest(BaseModel):
        geometry: dict = Field(
            ...,
            description="GeoJSON Polygon in [longitude, latitude] coordinate order.",
            json_schema_extra={"example": REQUEST_EXAMPLE["geometry"]},
        )
        business_type: str = Field(
            "pickup_point",
            description=(
                "Business type or alias. Use GET /business-types for the fixed catalog. "
                f"Primary values: {', '.join(supported_business_types())}."
            ),
            examples=["pickup_point", "coffee_shop", "пивнуха"],
        )
        h3_resolution: int = Field(9, ge=7, le=10, description="H3 grid resolution. MVP default is 9.")
        data_mode: Literal["live", "mock"] = Field(
            "live",
            description="live uses OSM/Overpass; mock explicitly uses the bundled PVZ demo sample.",
        )
        use_live_osm: bool | None = Field(
            None,
            description="Deprecated compatibility field. Use data_mode instead.",
        )
        allow_custom_business: bool = Field(
            True,
            description=(
                "When true, an unsupported business_type creates a custom OSM search profile instead of "
                "returning 422."
            ),
        )
        business_query: str | None = Field(
            None,
            min_length=2,
            max_length=120,
            description="Required user text when business_type is custom_osm.",
        )

    app = FastAPI(
        title="GeoPredict Analyze API",
        version="0.1.0",
        description=(
            "API для геомаркетингового анализа территории. "
            "Сервис принимает GeoJSON Polygon, строит H3-сетку, собирает/использует OSM POI "
            "и возвращает GeoJSON FeatureCollection с ML-оценкой успешности локации."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(
        "/business-types",
        tags=["analysis"],
        summary="List supported business types",
        response_description="Supported business catalog for analyze requests.",
        openapi_extra={
            "responses": {
                "200": {
                    "description": "Supported business catalog",
                    "content": {"application/json": {"example": BUSINESS_TYPES_EXAMPLE}},
                }
            }
        },
    )
    def business_types_endpoint(query: str | None = Query(None, description="Optional user search text.")) -> dict:
        catalog = suggest_business_profiles(query, limit=20) if query else business_type_catalog()
        result = {"total": len(catalog), "business_types": catalog}
        if query:
            result["custom_candidate"] = custom_business_candidate(query)
        return result

    @app.get("/health", tags=["system"], summary="Health check")
    def health() -> dict:
        return {"status": "ok", "service": "geopredict-api", "model_active": True}

    @app.post(
        "/analyze",
        tags=["analysis"],
        summary="Analyze territory suitability for a supported business type",
        response_description="GeoJSON FeatureCollection with suitability scores by H3 cell.",
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "example": REQUEST_EXAMPLE,
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Successful analysis",
                    "content": {"application/json": {"example": RESPONSE_EXAMPLE}},
                }
            },
        },
    )
    def analyze_endpoint(payload: AnalyzeRequest = Body(...)) -> dict:
        try:
            payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
            validate_analysis_area(
                payload_dict["geometry"],
                resolution=int(payload_dict.get("h3_resolution", 9)),
            )
            source = resolve_poi_source(payload_dict)
            return analyze_request(
                payload_dict,
                pois_geojson=source.geojson,
                data_sources=[source.source],
                data_warnings=list(source.warnings),
                data_fetched_at=source.fetched_at,
            )
        except DataSourceUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "osm_unavailable",
                    "message": str(exc),
                    "retryable": True,
                },
            ) from exc
        except MockDataUnavailableError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "mock_unavailable", "message": str(exc)},
            ) from exc
        except AnalysisAreaTooLargeError as exc:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "analysis_area_too_large",
                    "message": str(exc),
                    "estimated_cells": exc.estimated_cells,
                    "max_cells": exc.max_cells,
                },
            ) from exc
        except UnsupportedBusinessTypeError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "unsupported_business_type",
                    "message": str(exc),
                    "supported_business_types": list(exc.supported_business_types),
                    "suggestions": list(exc.suggestions),
                },
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Analysis dependency failed: {exc}") from exc
else:
    app = None


def analyze(payload: dict, pois_geojson: dict | None = None) -> dict:
    return analyze_request(payload, pois_geojson=pois_geojson)


def business_types(query: str | None = None) -> dict:
    catalog = suggest_business_profiles(query, limit=20) if query else business_type_catalog()
    result = {"total": len(catalog), "business_types": catalog}
    if query:
        result["custom_candidate"] = custom_business_candidate(query)
    return result
