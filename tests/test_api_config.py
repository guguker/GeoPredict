import os
import unittest
from unittest.mock import patch

from api.analyze import (
    DEFAULT_CORS_ORIGINS,
    DataSourceUnavailableError,
    MockDataUnavailableError,
    business_types,
    get_cors_origins,
    resolve_poi_source,
)


class ApiConfigTest(unittest.TestCase):
    def test_default_cors_origins_include_local_frontend(self):
        with patch.dict(os.environ, {}, clear=True):
            origins = get_cors_origins()

        self.assertEqual(origins, list(DEFAULT_CORS_ORIGINS))
        self.assertIn("http://localhost:3000", origins)

    def test_cors_origins_can_be_configured_from_env(self):
        with patch.dict(
            os.environ,
            {"GEOPREDICT_CORS_ORIGINS": "http://localhost:8080, https://example.com "},
        ):
            origins = get_cors_origins()

        self.assertEqual(origins, ["http://localhost:8080", "https://example.com"])

    def test_resolve_poi_source_raises_when_live_osm_fails(self):
        payload = {"geometry": {"type": "Polygon", "coordinates": []}, "data_mode": "live"}

        def failing_fetcher(_geometry):
            raise RuntimeError("HTTP Error 429: Too Many Requests")

        with self.assertRaises(DataSourceUnavailableError) as context:
            resolve_poi_source(payload, fetcher=failing_fetcher)

        self.assertIn("429", str(context.exception))

    def test_resolve_poi_source_marks_explicit_mock_data(self):
        payload = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[37.6173, 55.7558], [37.6273, 55.7558], [37.6273, 55.7658], [37.6173, 55.7558]]
                ],
            },
            "business_type": "pickup_point",
            "data_mode": "mock",
        }
        mock_geojson = {"type": "FeatureCollection", "features": []}

        source = resolve_poi_source(
            payload,
            fetcher=lambda _geometry: self.fail(),
            mock_loader=lambda _payload: mock_geojson,
        )

        self.assertEqual(source.geojson, mock_geojson)
        self.assertEqual(source.source, "mock_sample")
        self.assertTrue(source.warnings)

    def test_mock_is_rejected_for_unsupported_profile(self):
        payload = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[37.6173, 55.7558], [37.6273, 55.7558], [37.6273, 55.7658], [37.6173, 55.7558]]
                ],
            },
            "business_type": "coffee_shop",
            "data_mode": "mock",
        }

        with self.assertRaises(MockDataUnavailableError):
            resolve_poi_source(payload)

    def test_business_types_helper_returns_catalog_for_frontend(self):
        result = business_types()

        self.assertEqual(result["total"], 10)
        self.assertEqual(len(result["business_types"]), 10)
        self.assertEqual(result["business_types"][0]["business_type"], "pickup_point")

    def test_business_types_helper_filters_by_user_query(self):
        result = business_types(query="кофе")

        self.assertGreaterEqual(result["total"], 1)
        self.assertEqual(result["business_types"][0]["business_type"], "coffee_shop")
        self.assertEqual(result["custom_candidate"]["business_type"], "custom_osm")
        self.assertEqual(result["custom_candidate"]["source_query"], "кофе")


if __name__ == "__main__":
    unittest.main()
