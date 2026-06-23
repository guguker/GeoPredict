import tempfile
import unittest
from pathlib import Path

from geopredict_ml.business import get_business_profile, supported_business_types
from geopredict_ml.model_registry import (
    load_explicit_model,
    load_model_for_profile,
    model_artifact_path,
    train_all_registered_models,
)


class ModelRegistryTest(unittest.TestCase):
    def test_model_artifact_path_uses_business_type(self):
        coffee = get_business_profile("coffee_shop")

        path = model_artifact_path(coffee)

        self.assertEqual(path, Path("models/geopredict_coffee_shop_v1.pkl"))

    def test_train_all_registered_models_writes_one_artifact_per_business_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = train_all_registered_models(temp_dir)
            manifest = Path(temp_dir) / "manifest.json"

            for business_type in supported_business_types():
                self.assertTrue(model_artifact_path(business_type, models_dir=temp_dir).exists())

            pickup = load_model_for_profile(get_business_profile("pickup_point"), models_dir=temp_dir)
            self.assertTrue(manifest.exists())
            self.assertIsNotNone(pickup)
            self.assertEqual(pickup.business_type, "pickup_point")

        self.assertEqual(len(artifacts), 20)

    def test_rejects_explicit_model_for_wrong_business_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            train_all_registered_models(temp_dir)
            coffee_model = Path(temp_dir) / "geopredict_coffee_shop_v1.pkl"

            with self.assertRaises(ValueError):
                load_explicit_model(coffee_model, get_business_profile("pickup_point"))


if __name__ == "__main__":
    unittest.main()
