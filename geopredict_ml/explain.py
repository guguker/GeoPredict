from __future__ import annotations

from typing import Any

from .business import BusinessProfile

FACTOR_LABELS = {
    "traffic_potential": "Поток и доступность",
    "density_score": "Плотность POI",
    "residential_score": "Жилая база",
    "transport_score": "Транспорт",
    "retail_anchor_score": "Торговые якоря",
    "office_score": "Офисы",
    "education_score": "Образование рядом",
    "market_validation": "Подтвержденный спрос",
    "competition_penalty": "Перенасыщение конкурентами",
    "norm_competition": "Конкуренция",
}


def build_explanation(features: dict[str, Any], score: float, profile: BusinessProfile) -> list[str]:
    explanation: list[str] = []

    if score >= 0.75:
        explanation.append("Приоритетная локация")
    elif score >= 0.58:
        explanation.append("Перспективная локация")
    elif score >= 0.42:
        explanation.append("Средняя привлекательность локации")
    else:
        explanation.append("Локация требует осторожной проверки")

    competition = int(features.get("competition", 0))
    penalty = float(features.get("competition_penalty", 0.0))
    if competition == 0:
        explanation.append("Нет прямых конкурентов в радиусе анализа")
    elif penalty < 0.25:
        explanation.append("Конкуренция есть, но зона не выглядит перенасыщенной")
    else:
        explanation.append("Высокая концентрация конкурентов снижает оценку")

    if profile.business_type == "pickup_point":
        if float(features.get("residential_score", 0.0)) >= 0.45:
            explanation.append("Сильная жилая база для регулярных заказов")
        if float(features.get("market_validation", 0.0)) >= 0.35 and penalty < 0.6:
            explanation.append("Наличие ПВЗ рядом подтверждает спрос на выдачу заказов")

    if float(features.get("transport_score", 0.0)) >= 0.35:
        explanation.append("Хорошая транспортная доступность")
    if float(features.get("retail_anchor_score", 0.0)) >= 0.35:
        explanation.append("Рядом есть торговые и сервисные точки притяжения")
    if float(features.get("office_score", 0.0)) >= 0.35:
        explanation.append("Офисное окружение добавляет дневной поток")
    if float(features.get("density_score", 0.0)) < 0.20:
        explanation.append("Мало открытых POI-данных вокруг точки")

    return explanation[:6]


def build_explanation_factors(features: dict[str, Any], profile: BusinessProfile) -> list[dict[str, Any]]:
    factors: list[dict[str, Any]] = []
    for feature_name, weight in profile.target_weights.items():
        value = float(features.get(feature_name, 0.0))
        if weight < 0:
            impact = -value * abs(weight)
            direction = "negative" if value >= 0.20 else "neutral"
            message = "Снижает оценку из-за насыщения или прямой конкуренции"
        else:
            impact = value * weight
            direction = "positive" if value >= 0.35 else "negative" if value < 0.12 else "neutral"
            message = "Поддерживает оценку" if direction == "positive" else "Слабый сигнал для этой зоны"

        if direction == "neutral":
            continue
        factors.append(
            {
                "feature": feature_name,
                "label": FACTOR_LABELS.get(feature_name, feature_name),
                "value": round(value, 3),
                "weight": round(weight, 3),
                "impact": round(impact, 3),
                "direction": direction,
                "message": message,
            }
        )

    factors.sort(key=lambda item: abs(float(item["impact"])), reverse=True)
    return factors[:6]
