import unittest

from geopredict_ml.business import get_business_profile
from geopredict_ml.features import categorize_poi, compute_cell_features
from geopredict_ml.grid import GridCell


class PickupPointFeatureTest(unittest.TestCase):
    def test_pvz_profile_recognizes_major_marketplace_brands(self):
        profile = get_business_profile("pvz")
        examples = [
            {"name": "Ozon pickup point", "brand": "Ozon"},
            {"name": "Wildberries", "operator": "WB"},
            {"name": "Яндекс Маркет ПВЗ", "brand": "Яндекс Маркет"},
            {"name": "СДЭК", "brand": "CDEK"},
            {"name": "Boxberry", "office": "courier"},
            {"amenity": "parcel_locker", "name": "PickPoint"},
        ]

        for tags in examples:
            with self.subTest(tags=tags):
                category = categorize_poi(tags, profile)
                self.assertTrue(category.is_competitor)

    def test_compute_cell_features_counts_competitors_and_anchors(self):
        profile = get_business_profile("pickup_point")
        cell = GridCell(
            h3_id="test_cell",
            center_lon=37.0,
            center_lat=55.0,
            geometry={
                "type": "Polygon",
                "coordinates": [[[36.999, 54.999], [37.001, 54.999], [37.001, 55.001], [36.999, 55.001], [36.999, 54.999]]],
            },
        )
        pois = [
            {"lon": 37.0001, "lat": 55.0001, "tags": {"brand": "Ozon", "shop": "outpost"}},
            {"lon": 37.0002, "lat": 55.0002, "tags": {"highway": "bus_stop"}},
            {"lon": 37.0003, "lat": 55.0003, "tags": {"building": "apartments"}},
            {"lon": 37.0004, "lat": 55.0004, "tags": {"shop": "supermarket"}},
        ]

        features = compute_cell_features(cell, pois, profile)

        self.assertEqual(features["competition"], 1)
        self.assertEqual(features["poi_counts"]["competitors"], 1)
        self.assertEqual(features["poi_counts"]["public_transport"], 1)
        self.assertEqual(features["poi_counts"]["residential"], 1)
        self.assertGreater(features["traffic_potential"], 0)
        self.assertGreater(features["density_score"], 0)

    def test_competitor_matching_does_not_use_arbitrary_substrings(self):
        beer = get_business_profile("beer_store")
        car_service = get_business_profile("car_service")
        grocery = get_business_profile("grocery_store")

        self.assertFalse(categorize_poi({"name": "Барбарис", "amenity": "school"}, beer).is_competitor)
        self.assertFalse(categorize_poi({"name": "Остановка", "highway": "bus_stop"}, car_service).is_competitor)
        self.assertFalse(categorize_poi({"shop": "books", "name": "Книжный магазин"}, grocery).is_competitor)

        self.assertTrue(categorize_poi({"amenity": "pub", "name": "Local Pub"}, beer).is_competitor)
        self.assertTrue(categorize_poi({"shop": "car_repair", "name": "СТО"}, car_service).is_competitor)
        self.assertTrue(categorize_poi({"shop": "supermarket", "name": "Market"}, grocery).is_competitor)


if __name__ == "__main__":
    unittest.main()
