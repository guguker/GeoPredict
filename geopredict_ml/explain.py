from __future__ import annotations

from typing import Any

from .business import BusinessProfile


def _competitor_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "конкурентная точка"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "конкурентные точки"
    return "конкурентных точек"


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


def build_explanation_summary(features: dict[str, Any], score: float, profile: BusinessProfile) -> str:
    competition = int(features.get("competition", 0))
    penalty = float(features.get("competition_penalty", 0.0))
    strengths: list[str] = []

    if float(features.get("transport_score", 0.0)) >= 0.35:
        strengths.append("хорошая транспортная доступность")
    if float(features.get("retail_anchor_score", 0.0)) >= 0.35:
        strengths.append("сильное торгово-сервисное окружение")
    if float(features.get("residential_score", 0.0)) >= 0.35:
        strengths.append("плотное жилое окружение")
    if float(features.get("office_score", 0.0)) >= 0.35:
        strengths.append("дневной поток от офисов")

    if score >= 0.70:
        opening = "Локация входит в число наиболее перспективных"
    elif score >= 0.50:
        opening = "Локация выглядит умеренно перспективной"
    else:
        opening = "Локация требует дополнительной проверки"

    if strengths:
        opening += f": её поддерживают {', '.join(strengths[:2])}"

    radius = profile.radius_m
    if competition == 0:
        competition_text = f"Прямых конкурентов в радиусе {radius} м не найдено."
    elif penalty < 0.25:
        competition_text = (
            f"В радиусе {radius} м найдено {competition} {_competitor_word(competition)}, "
            "но уровень пока не считается перенасыщенным."
        )
    else:
        competition_text = (
            f"В радиусе {radius} м найдено {competition} {_competitor_word(competition)}, "
            "и их концентрация заметно снижает итоговую оценку."
        )

    return f"{opening}. {competition_text}"
