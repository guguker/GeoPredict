from __future__ import annotations

import math
from statistics import median


def regression_metrics(y_true: list[float], y_pred: list[float]) -> dict[str, float | int]:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if not y_true:
        raise ValueError("Cannot calculate metrics for an empty dataset")

    errors = [predicted - actual for actual, predicted in zip(y_true, y_pred)]
    absolute_errors = [abs(error) for error in errors]
    squared_errors = [error**2 for error in errors]

    mse = sum(squared_errors) / len(squared_errors)
    return {
        "count": len(y_true),
        "mae": sum(absolute_errors) / len(absolute_errors),
        "mse": mse,
        "rmse": math.sqrt(mse),
        "median_absolute_error": median(absolute_errors),
        "max_error": max(absolute_errors),
        "bias": sum(errors) / len(errors),
        "mape": _mean_absolute_percentage_error(y_true, absolute_errors),
        "r2": _r2_score(y_true, y_pred),
    }


def _mean_absolute_percentage_error(y_true: list[float], absolute_errors: list[float]) -> float:
    epsilon = 1e-9
    percentage_errors = [
        error / max(abs(actual), epsilon)
        for actual, error in zip(y_true, absolute_errors)
    ]
    return sum(percentage_errors) / len(percentage_errors)


def _r2_score(y_true: list[float], y_pred: list[float]) -> float:
    mean_true = sum(y_true) / len(y_true)
    total_variance = sum((actual - mean_true) ** 2 for actual in y_true)
    residual_variance = sum((actual - predicted) ** 2 for actual, predicted in zip(y_true, y_pred))
    if total_variance == 0:
        return 1.0 if residual_variance == 0 else 0.0
    return 1.0 - residual_variance / total_variance
