from __future__ import annotations

from dataclasses import dataclass
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from .geo import clamp
from .target import MODEL_FEATURES, reference_training_rows


@dataclass
class DecisionStump:
    feature_index: int
    threshold: float
    left_value: float
    right_value: float

    def predict_matrix(self, x: np.ndarray) -> np.ndarray:
        return np.where(x[:, self.feature_index] <= self.threshold, self.left_value, self.right_value)


class GradientBoostingRegressorLite:
    model_type = "GradientBoostingRegressorLite"
    model_version = "geo-boost-lite-v1"

    def __init__(
        self,
        feature_names: tuple[str, ...] = MODEL_FEATURES,
        n_estimators: int = 48,
        learning_rate: float = 0.12,
        max_thresholds: int = 12,
    ) -> None:
        self.feature_names = feature_names
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_thresholds = max_thresholds
        self.initial_prediction = 0.5
        self.stumps: list[DecisionStump] = []
        self.business_type: str | None = None
        self.profile_title: str | None = None
        self.model_family: str | None = None

    def fit(self, rows: list[dict[str, Any]], targets: list[float]) -> "GradientBoostingRegressorLite":
        if not rows:
            raise ValueError("Cannot train model without rows")
        x = self._rows_to_matrix(rows)
        y = np.asarray(targets, dtype=float)
        self.initial_prediction = float(np.mean(y))
        predictions = np.full_like(y, self.initial_prediction)
        self.stumps = []

        for _ in range(self.n_estimators):
            residual = y - predictions
            stump = self._best_stump(x, residual)
            if stump is None:
                break
            predictions = predictions + self.learning_rate * stump.predict_matrix(x)
            self.stumps.append(stump)
        return self

    def predict(self, rows: list[dict[str, Any]]) -> list[float]:
        x = self._rows_to_matrix(rows)
        predictions = np.full(x.shape[0], self.initial_prediction, dtype=float)
        for stump in self.stumps:
            predictions = predictions + self.learning_rate * stump.predict_matrix(x)
        return [round(clamp(float(value)), 6) for value in predictions]

    def predict_one(self, row: dict[str, Any]) -> float:
        return self.predict([row])[0]

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            pickle.dump(self, handle)

    @classmethod
    def load(cls, path: str | Path) -> "GradientBoostingRegressorLite":
        with Path(path).open("rb") as handle:
            model = pickle.load(handle)
        if not isinstance(model, cls):
            raise TypeError(f"Unexpected model artifact type: {type(model)!r}")
        return model

    def _rows_to_matrix(self, rows: list[dict[str, Any]]) -> np.ndarray:
        return np.asarray([[float(row.get(name, 0.0)) for name in self.feature_names] for row in rows], dtype=float)

    def _best_stump(self, x: np.ndarray, residual: np.ndarray) -> DecisionStump | None:
        best_stump: DecisionStump | None = None
        best_loss = float("inf")

        for feature_index in range(x.shape[1]):
            values = x[:, feature_index]
            thresholds = self._candidate_thresholds(values)
            for threshold in thresholds:
                left_mask = values <= threshold
                right_mask = ~left_mask
                if not left_mask.any() or not right_mask.any():
                    continue
                left_value = float(np.mean(residual[left_mask]))
                right_value = float(np.mean(residual[right_mask]))
                fitted = np.where(left_mask, left_value, right_value)
                loss = float(np.mean((residual - fitted) ** 2))
                if loss < best_loss:
                    best_loss = loss
                    best_stump = DecisionStump(feature_index, float(threshold), left_value, right_value)
        return best_stump

    def _candidate_thresholds(self, values: np.ndarray) -> np.ndarray:
        unique = np.unique(values)
        if len(unique) <= self.max_thresholds:
            return unique
        quantiles = np.linspace(0.05, 0.95, self.max_thresholds)
        return np.unique(np.quantile(values, quantiles))


def train_reference_model(profile: Any) -> GradientBoostingRegressorLite:
    rows, targets = reference_training_rows(profile)
    model = GradientBoostingRegressorLite().fit(rows, targets)
    model.business_type = profile.business_type
    model.profile_title = profile.title
    model.model_family = getattr(profile, "model_family", profile.business_type)
    return model
