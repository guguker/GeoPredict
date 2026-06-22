from __future__ import annotations

import csv
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
