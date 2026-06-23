import unittest

from geopredict_ml.business import PROFILE_LIST, UnsupportedBusinessTypeError
from geopredict_ml.pipeline import _recommendation_for_candidate, analyze_request


SAMPLE_REQUEST = {
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [37.6173, 55.7558],
                [37.6213, 55.7558],
                [37.6213, 55.7598],
                [37.6173, 55.7598],
                [37.6173, 55.7558],
            ]
        ],
    },
    "business_type": "pickup_point",
    "h3_resolution": 9,
}


SAMPLE_POIS = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [37.6182, 55.7565]},
            "properties": {"name": "Ozon", "brand": "Ozon", "shop": "outpost"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [37.6192, 55.7575]},
            "properties": {"name": "Wildberries", "brand": "Wildberries", "shop": "outpost"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [37.6200, 55.7580]},
            "properties": {"highway": "bus_stop", "name": "Bus stop"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [37.6204, 55.7585]},
            "properties": {"building": "apartments"},
        },
    ],
}


class AnalyzeContractTest(unittest.TestCase):
    def test_analyze_returns_feature_collection_contract(self):
        result = analyze_request(SAMPLE_REQUEST, pois_geojson=SAMPLE_POIS)

        self.assertEqual(result["type"], "FeatureCollection")
        self.assertGreater(result["metadata"]["total_hexagons"], 0)
        self.assertEqual(result["metadata"]["business_type"], "pickup_point")
        self.assertTrue(result["metadata"]["model_active"])
        self.assertIn("model_version", result["metadata"])
        self.assertIn("model_source", result["metadata"])
        self.assertIn("model_artifact_path", result["metadata"])
        self.assertIn("top_candidates", result["metadata"])
        self.assertIn("recommendation_counts", result["metadata"])
        self.assertIn("selection_policy", result["metadata"])
        self.assertEqual(result["metadata"]["data_status"], "live")
        self.assertEqual(result["metadata"]["poi_count"], len(SAMPLE_POIS["features"]))
        self.assertGreaterEqual(len(result["metadata"]["top_candidates"]), 1)

        first = result["features"][0]
        self.assertEqual(first["type"], "Feature")
        self.assertEqual(first["geometry"]["type"], "Polygon")
        props = first["properties"]
        self.assertIn("h3_id", props)
        self.assertIn("rank", props)
        self.assertIn("suitability", props)
        self.assertIn("success_probability", props)
        self.assertIn("model_score", props)
        self.assertIn("selection_score", props)
        self.assertIn("data_confidence", props)
        self.assertIn("recommendation", props)
        self.assertIn("recommendation_label", props)
        self.assertIn("traffic_potential", props)
        self.assertIn("density_score", props)
        self.assertIn("poi_counts", props)
        self.assertIsInstance(props["explanation"], list)

    def test_top_candidate_matches_best_ranked_feature(self):
        result = analyze_request(SAMPLE_REQUEST, pois_geojson=SAMPLE_POIS)

        top = result["metadata"]["top_candidates"][0]
        ranked_first = min(result["features"], key=lambda feature: feature["properties"]["rank"])

        self.assertEqual(top["rank"], 1)
        self.assertEqual(top["h3_id"], ranked_first["properties"]["h3_id"])
        self.assertEqual(top["suitability"], ranked_first["properties"]["suitability"])

    def test_fallback_without_pois_is_not_marked_as_priority(self):
        result = analyze_request(
            SAMPLE_REQUEST,
            pois_geojson=None,
            data_sources=["osm_unavailable"],
            data_warnings=["OSM unavailable"],
        )

        self.assertEqual(result["metadata"]["data_sources"], ["osm_unavailable"])
        self.assertEqual(result["metadata"]["data_status"], "degraded")
        self.assertEqual(result["metadata"]["data_warnings"], ["OSM unavailable"])
        self.assertEqual(result["metadata"]["recommendation_counts"]["high_priority"], 0)
        self.assertTrue(
            all(feature["properties"]["recommendation"] != "high_priority" for feature in result["features"])
        )

    def test_high_priority_requires_top_rank_not_only_high_score(self):
        candidate = {"selection_score": 0.9, "data_confidence": 0.9}

        top = _recommendation_for_candidate(candidate, rank=1, total_cells=1_000)
        late = _recommendation_for_candidate(candidate, rank=50, total_cells=1_000)

        self.assertEqual(top["code"], "high_priority")
        self.assertNotEqual(late["code"], "high_priority")

    def test_rejects_invalid_geometry(self):
        bad_request = {"geometry": {"type": "Point", "coordinates": [37.6, 55.7]}, "business_type": "pickup_point"}

        with self.assertRaises(ValueError):
            analyze_request(bad_request, pois_geojson=SAMPLE_POIS)

    def test_rejects_unsupported_business_type(self):
        bad_request = SAMPLE_REQUEST | {"business_type": "unknown_business", "allow_custom_business": False}

        with self.assertRaises(UnsupportedBusinessTypeError) as context:
            analyze_request(bad_request, pois_geojson=SAMPLE_POIS)

        self.assertIn("coffee_shop", context.exception.supported_business_types)

    def test_unknown_business_type_uses_custom_osm_profile_by_default(self):
        request = SAMPLE_REQUEST | {"business_type": "рыболовный магазин"}
        result = analyze_request(request, pois_geojson=SAMPLE_POIS)

        self.assertEqual(result["metadata"]["business_type"], "custom_osm")
        self.assertTrue(result["metadata"]["is_custom_business"])
        self.assertEqual(result["metadata"]["business_query"], "рыболовный магазин")
        self.assertEqual(result["metadata"]["model_source"], "reference_in_memory")

    def test_all_catalog_titles_use_registered_models_not_custom_fallback(self):
        for profile in PROFILE_LIST:
            result = analyze_request(SAMPLE_REQUEST | {"business_type": profile.title}, pois_geojson=SAMPLE_POIS)
            self.assertEqual(result["metadata"]["business_type"], profile.business_type)
            self.assertFalse(result["metadata"]["is_custom_business"])
            self.assertEqual(result["metadata"]["model_source"], "registered_artifact")


if __name__ == "__main__":
    unittest.main()
