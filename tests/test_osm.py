import unittest

from geopredict_ml.osm import build_overpass_query


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


if __name__ == "__main__":
    unittest.main()
