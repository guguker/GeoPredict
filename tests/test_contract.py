import unittest

from geopredict_ml.pipeline import analyze_request


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

        first = result["features"][0]
        self.assertEqual(first["type"], "Feature")
        self.assertEqual(first["geometry"]["type"], "Polygon")
        props = first["properties"]
        self.assertIn("h3_id", props)
        self.assertIn("suitability", props)
        self.assertIn("success_probability", props)
        self.assertIn("traffic_potential", props)
        self.assertIn("density_score", props)
        self.assertIn("poi_counts", props)
        self.assertIsInstance(props["explanation"], list)

    def test_rejects_invalid_geometry(self):
        bad_request = {"geometry": {"type": "Point", "coordinates": [37.6, 55.7]}, "business_type": "pickup_point"}

        with self.assertRaises(ValueError):
            analyze_request(bad_request, pois_geojson=SAMPLE_POIS)


if __name__ == "__main__":
    unittest.main()
