import csv
import tempfile
import unittest
from pathlib import Path

from geopredict_ml.evaluation import fit_holdout_evaluation, load_labeled_dataset, ranking_metrics
from geopredict_ml.target import MODEL_FEATURES


class EvaluationTest(unittest.TestCase):
    def test_loads_dataset_and_runs_holdout_evaluation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = Path(temp_dir) / "dataset.csv"
            fieldnames = [*MODEL_FEATURES, "target_success"]
            rows = []
            for index in range(8):
                signal = index / 7.0
                row = {name: 0.0 for name in MODEL_FEATURES}
                row["traffic_potential"] = signal
                row["density_score"] = signal
                row["residential_score"] = signal
                row["transport_score"] = signal
                row["target_success"] = 0.2 + 0.6 * signal
                rows.append(row)

            with dataset_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            dataset = load_labeled_dataset(dataset_path)
            report = fit_holdout_evaluation(dataset, test_size=0.25, seed=7)

        self.assertEqual(report["mode"], "fit_holdout")
        self.assertEqual(report["train_rows"], 6)
        self.assertEqual(report["test_rows"], 2)
        self.assertIn("mae", report["model_metrics"])
        self.assertIn("rmse", report["model_metrics"])
        self.assertIn("baseline_metrics", report)

    def test_ranking_metrics_measure_top_k_quality(self):
        report = ranking_metrics([1.0, 0.0, 1.0, 0.0], [0.9, 0.2, 0.7, 0.1], k=2)

        self.assertEqual(report["k"], 2)
        self.assertEqual(report["positives"], 2)
        self.assertEqual(report["precision_at_k"], 1.0)
        self.assertEqual(report["recall_at_k"], 1.0)
        self.assertGreater(report["ndcg_at_k"], 0.0)
        self.assertGreater(report["lift_at_k"], 1.0)


if __name__ == "__main__":
    unittest.main()
