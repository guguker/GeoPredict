import unittest

from geopredict_ml.model import GradientBoostingRegressorLite


class ModelTest(unittest.TestCase):
    def test_gradient_boosting_lite_learns_monotonic_signal(self):
        rows = []
        targets = []
        for i in range(30):
            traffic = i / 29
            rows.append(
                {
                    "traffic_potential": traffic,
                    "density_score": traffic,
                    "norm_competition": 0.1,
                    "market_validation": 0.5,
                    "residential_score": traffic,
                    "transport_score": traffic,
                    "retail_anchor_score": traffic,
                    "office_score": 0.2,
                }
            )
            targets.append(0.15 + 0.75 * traffic)

        model = GradientBoostingRegressorLite(n_estimators=25, learning_rate=0.2, max_thresholds=8)
        model.fit(rows, targets)

        low = model.predict_one(rows[2])
        high = model.predict_one(rows[-2])

        self.assertLess(low, high)
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(high, 1.0)


if __name__ == "__main__":
    unittest.main()
