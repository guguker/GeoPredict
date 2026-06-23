import unittest
import tempfile

from geopredict_ml.cache import write_json_cache
from geopredict_ml.osm import build_overpass_query, fetch_overpass_geojson, overpass_cache_key


SAMPLE_POLYGON = {
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
}


class OverpassQueryTest(unittest.TestCase):
    def test_query_collects_broad_business_tags_for_custom_profiles(self):
        query = build_overpass_query(SAMPLE_POLYGON)

        self.assertIn('["shop"]', query)
        self.assertIn('["amenity"]', query)
        self.assertIn('["craft"]', query)
        self.assertIn('["tourism"]', query)

    def test_query_can_target_historical_overpass_snapshot(self):
        query = build_overpass_query(SAMPLE_POLYGON, snapshot_date="2024-01-01T00:00:00Z")

        self.assertIn('[date:"2024-01-01T00:00:00Z"]', query)

    def test_fetch_uses_cached_overpass_geojson_before_network(self):
        cached = {"type": "FeatureCollection", "features": []}
        with tempfile.TemporaryDirectory() as temp_dir:
            write_json_cache(temp_dir, overpass_cache_key(SAMPLE_POLYGON), cached)

            result = fetch_overpass_geojson(SAMPLE_POLYGON, overpass_url="http://invalid.local", cache_dir=temp_dir)

        self.assertEqual(result, cached)


if __name__ == "__main__":
    unittest.main()
