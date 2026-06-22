import math
import unittest

from geopredict_ml.metrics import regression_metrics


class RegressionMetricsTest(unittest.TestCase):
    def test_regression_metrics_known_values(self):
        metrics = regression_metrics([1.0, 2.0, 3.0], [1.0, 2.5, 2.0])

        self.assertEqual(metrics["count"], 3)
        self.assertAlmostEqual(metrics["mae"], 0.5)
        self.assertAlmostEqual(metrics["mse"], 1.25 / 3.0)
        self.assertAlmostEqual(metrics["rmse"], math.sqrt(1.25 / 3.0))
        self.assertAlmostEqual(metrics["median_absolute_error"], 0.5)
        self.assertAlmostEqual(metrics["max_error"], 1.0)
        self.assertAlmostEqual(metrics["bias"], -0.5 / 3.0)
        self.assertAlmostEqual(metrics["mape"], (0.0 + 0.25 + 1.0 / 3.0) / 3.0)
        self.assertAlmostEqual(metrics["r2"], 0.375)

    def test_rejects_empty_metric_input(self):
        with self.assertRaises(ValueError):
            regression_metrics([], [])

    def test_rejects_mismatched_metric_input(self):
        with self.assertRaises(ValueError):
            regression_metrics([1.0], [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
