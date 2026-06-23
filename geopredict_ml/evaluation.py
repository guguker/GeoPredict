from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .metrics import regression_metrics
from .model import GradientBoostingRegressorLite
from .target import MODEL_FEATURES


@dataclass(frozen=True)
class LabeledDataset:
    rows: list[dict[str, float]]
    targets: list[float]
    target_column: str


def load_labeled_dataset(path: str | Path, target_column: str = "target_success") -> LabeledDataset:
    rows: list[dict[str, float]] = []
    targets: list[float] = []

    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Dataset CSV must contain a header row")
        missing_features = [name for name in MODEL_FEATURES if name not in reader.fieldnames]
        if missing_features:
            raise ValueError(f"Dataset is missing model feature columns: {missing_features}")
        if target_column not in reader.fieldnames:
            raise ValueError(f"Dataset is missing target column: {target_column!r}")

        for raw_row in reader:
            rows.append({name: float(raw_row.get(name) or 0.0) for name in MODEL_FEATURES})
            targets.append(float(raw_row[target_column]))

    if not rows:
        raise ValueError("Dataset CSV must contain at least one data row")
    return LabeledDataset(rows=rows, targets=targets, target_column=target_column)


def evaluate_model(model: GradientBoostingRegressorLite, dataset: LabeledDataset) -> dict[str, float | int]:
    predictions = model.predict(dataset.rows)
    return regression_metrics(dataset.targets, predictions)


def evaluate_mean_baseline(dataset: LabeledDataset, baseline_value: float | None = None) -> dict[str, float | int]:
    value = sum(dataset.targets) / len(dataset.targets) if baseline_value is None else baseline_value
    predictions = [value for _ in dataset.targets]
    return regression_metrics(dataset.targets, predictions)


def train_test_split(
    dataset: LabeledDataset,
    test_size: float = 0.25,
    seed: int = 42,
) -> tuple[LabeledDataset, LabeledDataset]:
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be between 0 and 1")
    if len(dataset.rows) < 2:
        raise ValueError("At least two rows are required for train/test split")

    indexes = list(range(len(dataset.rows)))
    random.Random(seed).shuffle(indexes)
    test_count = max(1, min(len(indexes) - 1, round(len(indexes) * test_size)))
    test_indexes = set(indexes[:test_count])

    train_rows: list[dict[str, float]] = []
    train_targets: list[float] = []
    test_rows: list[dict[str, float]] = []
    test_targets: list[float] = []

    for index, row in enumerate(dataset.rows):
        if index in test_indexes:
            test_rows.append(row)
            test_targets.append(dataset.targets[index])
        else:
            train_rows.append(row)
            train_targets.append(dataset.targets[index])

    return (
        LabeledDataset(train_rows, train_targets, dataset.target_column),
        LabeledDataset(test_rows, test_targets, dataset.target_column),
    )


def fit_holdout_evaluation(
    dataset: LabeledDataset,
    test_size: float = 0.25,
    seed: int = 42,
    model_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    train, test = train_test_split(dataset, test_size=test_size, seed=seed)
    model = GradientBoostingRegressorLite(**(model_kwargs or {})).fit(train.rows, train.targets)
    train_mean = sum(train.targets) / len(train.targets)

    return {
        "mode": "fit_holdout",
        "target_column": dataset.target_column,
        "train_rows": len(train.rows),
        "test_rows": len(test.rows),
        "test_size": test_size,
        "seed": seed,
        "model_metrics": evaluate_model(model, test),
        "baseline_metrics": evaluate_mean_baseline(test, baseline_value=train_mean),
        "baseline": "train_mean",
        "model_type": model.model_type,
        "model_version": model.model_version,
    }


def ranking_metrics(
    labels: list[float],
    scores: list[float],
    k: int = 10,
    relevance_threshold: float = 0.5,
) -> dict[str, float | int]:
    if len(labels) != len(scores):
        raise ValueError("labels and scores must have the same length")
    if not labels:
        raise ValueError("ranking metrics require at least one row")
    if k <= 0:
        raise ValueError("k must be positive")

    cutoff = min(k, len(labels))
    rows = list(zip(labels, scores))
    ordered = sorted(rows, key=lambda item: item[1], reverse=True)
    top = ordered[:cutoff]
    positives = sum(1 for label, _score in rows if label >= relevance_threshold)
    top_positives = sum(1 for label, _score in top if label >= relevance_threshold)
    top_label_mean = sum(label for label, _score in top) / cutoff
    global_label_mean = sum(labels) / len(labels)

    return {
        "rows": len(labels),
        "k": cutoff,
        "positives": positives,
        "precision_at_k": round(top_positives / cutoff, 6),
        "recall_at_k": round(top_positives / max(1, positives), 6),
        "ndcg_at_k": round(_ndcg_at_k(ordered, cutoff), 6),
        "lift_at_k": round(top_label_mean / global_label_mean, 6) if global_label_mean > 0 else 0.0,
    }


def _ndcg_at_k(ordered_rows: list[tuple[float, float]], k: int) -> float:
    dcg = _discounted_gain([label for label, _score in ordered_rows[:k]])
    ideal = sorted((label for label, _score in ordered_rows), reverse=True)[:k]
    idcg = _discounted_gain(ideal)
    return dcg / idcg if idcg > 0 else 0.0


def _discounted_gain(labels: list[float]) -> float:
    return sum((2**max(0.0, label) - 1.0) / math.log2(index + 2) for index, label in enumerate(labels))
