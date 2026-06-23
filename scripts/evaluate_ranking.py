from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from geopredict_ml.evaluation import ranking_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate GeoPredict ranking metrics from a CSV.")
    parser.add_argument("--dataset", required=True, help="CSV with label and score columns.")
    parser.add_argument("--label-column", default="target_success", help="Ground-truth or proxy label column.")
    parser.add_argument("--score-column", default="selection_score", help="Model/ranking score column.")
    parser.add_argument("--k", type=int, default=10, help="Top-K cutoff.")
    parser.add_argument("--relevance-threshold", type=float, default=0.5, help="Positive label threshold.")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()

    labels: list[float] = []
    scores: list[float] = []
    with Path(args.dataset).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            labels.append(float(row[args.label_column]))
            scores.append(float(row[args.score_column]))

    report = ranking_metrics(labels, scores, k=args.k, relevance_threshold=args.relevance_threshold)
    report.update(
        {
            "mode": "ranking",
            "label_column": args.label_column,
            "score_column": args.score_column,
            "relevance_threshold": args.relevance_threshold,
        }
    )

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
