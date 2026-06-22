from __future__ import annotations

import argparse
import json
from pathlib import Path

from geopredict_ml.evaluation import (
    evaluate_mean_baseline,
    evaluate_model,
    fit_holdout_evaluation,
    load_labeled_dataset,
)
from geopredict_ml.model import GradientBoostingRegressorLite


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate GeoPredict regression model metrics.")
    parser.add_argument("--dataset", required=True, help="CSV with model features and target column.")
    parser.add_argument("--target-column", default="target_success", help="Target column name in dataset CSV.")
    parser.add_argument("--model", help="Optional model artifact path to evaluate on the full dataset.")
    parser.add_argument(
        "--fit-holdout",
        action="store_true",
        help="Train a fresh model on a deterministic train split and evaluate it on holdout rows.",
    )
    parser.add_argument("--test-size", type=float, default=0.25, help="Holdout fraction for --fit-holdout.")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic split seed for --fit-holdout.")
    parser.add_argument("--output", help="Optional path for metrics JSON.")
    args = parser.parse_args()

    dataset = load_labeled_dataset(args.dataset, target_column=args.target_column)

    if args.fit_holdout:
        report = fit_holdout_evaluation(dataset, test_size=args.test_size, seed=args.seed)
    else:
        if not args.model:
            parser.error("--model is required unless --fit-holdout is used")
        model = GradientBoostingRegressorLite.load(args.model)
        report = {
            "mode": "artifact_full_dataset",
            "target_column": dataset.target_column,
            "rows": len(dataset.rows),
            "model_path": args.model,
            "model_type": model.model_type,
            "model_version": model.model_version,
            "model_metrics": evaluate_model(model, dataset),
            "baseline_metrics": evaluate_mean_baseline(dataset),
            "baseline": "dataset_mean",
        }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
