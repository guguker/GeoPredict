import unittest

from geopredict_ml.business import get_business_profile
from geopredict_ml.osm_history import business_snapshot_diff


def feature(osm_id, lon, lat, tags):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"osm_id": osm_id, "osm_type": "node"} | tags,
    }


class OsmHistoryTest(unittest.TestCase):
    def test_snapshot_diff_detects_appeared_and_disappeared_business_pois(self):
        profile = get_business_profile("pickup_point")
        before = {
            "type": "FeatureCollection",
            "features": [
                feature(1, 37.1, 55.1, {"shop": "outpost", "brand": "Ozon"}),
                feature(2, 37.2, 55.2, {"amenity": "cafe", "name": "Coffee"}),
            ],
        }
        after = {
            "type": "FeatureCollection",
            "features": [
                feature(1, 37.1, 55.1, {"shop": "outpost", "brand": "Ozon"}),
                feature(3, 37.3, 55.3, {"shop": "outpost", "brand": "Wildberries"}),
            ],
        }

        report = business_snapshot_diff(before, after, profile)

        self.assertEqual(report["summary"]["before_count"], 1)
        self.assertEqual(report["summary"]["after_count"], 2)
        self.assertEqual(report["summary"]["appeared_count"], 1)
        self.assertEqual(report["appeared"][0]["poi_id"], "osm:node:3")


if __name__ == "__main__":
    unittest.main()
