from __future__ import annotations

from geopredict_ml.osm import fetch_overpass_geojson
from geopredict_ml.pipeline import analyze_request


try:
    from fastapi import Body, FastAPI, HTTPException
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - optional web dependency
    Body = None
    BaseModel = object
    FastAPI = None
    Field = None
    HTTPException = Exception


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
                "suitability": 0.742,
                "success_probability": 0.742,
                "recommendation": "promising",
                "recommendation_label": "Перспективная зона",
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
        "data_sources": ["osm"],
        "model_active": True,
        "model_type": "GradientBoostingRegressorLite",
        "model_version": "geo-boost-lite-v1",
        "target_type": "proxy_location_success",
        "grid_backend": "h3",
        "top_candidates": [
            {
                "h3_id": "891f1d489ffffff",
                "rank": 1,
                "suitability": 0.742,
                "recommendation": "promising",
                "center": {"lon": 37.6173, "lat": 55.7558},
            }
        ],
        "recommendation_counts": {
            "high_priority": 4,
            "promising": 21,
            "manual_review": 14,
            "low_priority": 3,
        },
    },
}


if FastAPI:
    class AnalyzeRequest(BaseModel):
        geometry: dict = Field(
            ...,
            description="GeoJSON Polygon in [longitude, latitude] coordinate order.",
            json_schema_extra={"example": REQUEST_EXAMPLE["geometry"]},
        )
        business_type: str = Field(
            "pickup_point",
            description="Business type. For PVZ use pickup_point, pvz, ozon, wb, wildberries, yandex market aliases.",
            examples=["pickup_point"],
        )
        h3_resolution: int = Field(9, ge=7, le=10, description="H3 grid resolution. MVP default is 9.")
        use_live_osm: bool = Field(
            True,
            description="When true, the API fetches OpenStreetMap POIs through Overpass before scoring.",
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

    @app.get("/health", tags=["system"], summary="Health check")
    def health() -> dict:
        return {"status": "ok", "service": "geopredict-api", "model_active": True}

    @app.post(
        "/analyze",
        tags=["analysis"],
        summary="Analyze territory suitability for a pickup point or retail business",
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
            pois = fetch_overpass_geojson(payload_dict["geometry"]) if payload_dict.get("use_live_osm", True) else None
            return analyze_request(payload_dict, pois_geojson=pois)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Analysis dependency failed: {exc}") from exc
else:
    app = None


def analyze(payload: dict, pois_geojson: dict | None = None) -> dict:
    return analyze_request(payload, pois_geojson=pois_geojson)
