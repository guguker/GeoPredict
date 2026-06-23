import unittest
import tempfile
from pathlib import Path

from geopredict_ml.business import (
    UnsupportedBusinessTypeError,
    build_custom_business_profile,
    business_search_summary,
    business_type_catalog,
    get_business_profile,
    load_business_profiles,
    resolve_business_profile,
    suggest_business_profiles,
    supported_business_types,
)
from geopredict_ml.features import categorize_poi


class BusinessProfileCatalogTest(unittest.TestCase):
    def test_catalog_contains_fixed_twenty_business_types(self):
        catalog = business_type_catalog()
        business_types = supported_business_types()

        self.assertEqual(len(catalog), 20)
        self.assertEqual(len(business_types), 20)
        self.assertEqual(len(set(business_types)), 20)
        self.assertIn("pickup_point", business_types)
        self.assertIn("coffee_shop", business_types)
        self.assertIn("beer_store", business_types)

    def test_loads_business_profiles_from_yml_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "custom.yml"
            config.write_text(
                """
{
  "profiles": [
    {
      "business_type": "test_shop",
      "title": "Тестовый магазин",
      "category": "test",
      "aliases": ["тест"],
      "competitor_keywords": ["test"],
      "competitor_tag_values": ["test"],
      "radius_m": 321,
      "target_weights": "convenience_retail"
    }
  ]
}
""".strip(),
                encoding="utf-8",
            )

            profiles = load_business_profiles(temp_dir)

        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].business_type, "test_shop")
        self.assertEqual(profiles[0].radius_m, 321)

    def test_aliases_resolve_to_primary_business_types(self):
        self.assertEqual(get_business_profile("кофейня").business_type, "coffee_shop")
        self.assertEqual(get_business_profile("пивнуха").business_type, "beer_store")
        self.assertEqual(get_business_profile("ozon").business_type, "pickup_point")
        self.assertEqual(get_business_profile("стоматология").business_type, "dental_clinic")
        self.assertEqual(get_business_profile("💅 Маникюр").business_type, "nail_salon")
        self.assertEqual(get_business_profile("🍺 Пивной магазин").business_type, "beer_store")

    def test_profile_titles_resolve_to_primary_business_types(self):
        for profile in load_business_profiles():
            self.assertEqual(get_business_profile(profile.title).business_type, profile.business_type)

    def test_frontend_display_labels_resolve_to_primary_business_types(self):
        labels = {
            "Магазин у дома": "retail",
            "Продуктовый магазин": "grocery_store",
            "Фастфуд": "fast_food",
            "Пивной магазин": "beer_store",
            "Салон красоты": "beauty_salon",
            "Маникюр": "nail_salon",
            "Медицинская клиника": "medical_clinic",
            "Цветочный магазин": "flower_shop",
            "Автосервис": "car_service",
            "Детский центр": "children_education",
        }

        for label, business_type in labels.items():
            self.assertEqual(get_business_profile(label).business_type, business_type)

    def test_unsupported_business_type_lists_supported_values(self):
        with self.assertRaises(UnsupportedBusinessTypeError) as context:
            get_business_profile("кофе и десерты")

        self.assertIn("coffee_shop", context.exception.supported_business_types)
        self.assertIn("pickup_point", context.exception.supported_business_types)
        self.assertIn("coffee_shop", context.exception.suggestions)

    def test_suggest_business_profiles_for_user_query(self):
        coffee_suggestions = suggest_business_profiles("кофе")
        beer_suggestions = suggest_business_profiles("разливное")

        self.assertEqual(coffee_suggestions[0]["business_type"], "coffee_shop")
        self.assertEqual(beer_suggestions[0]["business_type"], "beer_store")

    def test_resolve_business_profile_builds_custom_osm_profile(self):
        profile = resolve_business_profile("рыболовный магазин")

        self.assertEqual(profile.business_type, "custom_osm")
        self.assertTrue(profile.is_custom)
        self.assertIn("fishing", profile.competitor_tag_values)

    def test_custom_osm_profile_detects_hint_tags(self):
        profile = build_custom_business_profile("рыболовный магазин")

        self.assertTrue(categorize_poi({"shop": "fishing", "name": "Fishing Pro"}, profile).is_competitor)
        summary = business_search_summary(profile)
        self.assertEqual(summary["mode"], "custom_osm")
        self.assertIn("fishing", summary["osm_tag_values"])
        self.assertIn("shop", summary["osm_tag_keys"])

    def test_business_specific_competitor_detection(self):
        coffee = get_business_profile("coffee_shop")
        beer = get_business_profile("beer_store")

        self.assertTrue(categorize_poi({"amenity": "cafe", "name": "Coffee To Go"}, coffee).is_competitor)
        self.assertTrue(categorize_poi({"shop": "alcohol", "name": "Разливное пиво"}, beer).is_competitor)


if __name__ == "__main__":
    unittest.main()
