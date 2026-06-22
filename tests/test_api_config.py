import os
import unittest
from unittest.mock import patch

from api.analyze import DEFAULT_CORS_ORIGINS, business_types, get_cors_origins, resolve_poi_source


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

    def test_resolve_poi_source_falls_back_when_live_osm_fails(self):
        payload = {"geometry": {"type": "Polygon", "coordinates": []}, "use_live_osm": True}

        def failing_fetcher(_geometry):
            raise RuntimeError("HTTP Error 429: Too Many Requests")

        pois, data_sources, data_warnings = resolve_poi_source(payload, fetcher=failing_fetcher)

        self.assertIsNone(pois)
        self.assertEqual(data_sources, ["osm_unavailable"])
        self.assertEqual(len(data_warnings), 1)
        self.assertIn("fallback scoring", data_warnings[0])

    def test_resolve_poi_source_skips_fetcher_when_live_osm_disabled(self):
        payload = {"geometry": {"type": "Polygon", "coordinates": []}, "use_live_osm": False}

        pois, data_sources, data_warnings = resolve_poi_source(payload, fetcher=lambda _geometry: self.fail())

        self.assertIsNone(pois)
        self.assertEqual(data_sources, [])
        self.assertEqual(data_warnings, [])

    def test_business_types_helper_returns_catalog_for_frontend(self):
        result = business_types()

        self.assertEqual(result["total"], 20)
        self.assertEqual(len(result["business_types"]), 20)
        self.assertEqual(result["business_types"][0]["business_type"], "pickup_point")

    def test_business_types_helper_filters_by_user_query(self):
        result = business_types(query="кофе")

        self.assertGreaterEqual(result["total"], 1)
        self.assertEqual(result["business_types"][0]["business_type"], "coffee_shop")
        self.assertEqual(result["custom_candidate"]["business_type"], "custom_osm")
        self.assertEqual(result["custom_candidate"]["source_query"], "кофе")


if __name__ == "__main__":
    unittest.main()
