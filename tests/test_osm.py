import json
import tempfile
import unittest

from geopredict_ml.osm import build_overpass_query, fetch_overpass_result


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
        self.assertIn("craft", query)
        self.assertIn("tourism", query)

    def test_fetch_uses_second_endpoint_and_then_cache(self):
        attempts = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {
                        "elements": [
                            {"type": "node", "id": 1, "lon": 37.62, "lat": 55.76, "tags": {"amenity": "cafe"}}
                        ]
                    }
                ).encode()

        def opener(http_request, timeout):
            attempts.append((http_request.full_url, timeout))
            if len(attempts) == 1:
                raise TimeoutError("first endpoint timeout")
            return Response()

        with tempfile.TemporaryDirectory() as cache_dir:
            first = fetch_overpass_result(
                SAMPLE_POLYGON,
                overpass_urls=("https://first.invalid", "https://second.invalid"),
                cache_dir=cache_dir,
                opener=opener,
            )
            cached = fetch_overpass_result(
                SAMPLE_POLYGON,
                overpass_urls=("https://unused.invalid",),
                cache_dir=cache_dir,
                opener=lambda *_args, **_kwargs: self.fail("cache should avoid network"),
            )

        self.assertEqual(len(attempts), 2)
        self.assertEqual(first.source, "osm_live")
        self.assertEqual(first.endpoint, "https://second.invalid")
        self.assertEqual(cached.source, "osm_cache")
        self.assertEqual(len(cached.geojson["features"]), 1)


if __name__ == "__main__":
    unittest.main()
