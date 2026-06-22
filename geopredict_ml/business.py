from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).lower()
    text = text.replace("ё", "е")
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class BusinessProfile:
    business_type: str
    title: str
    aliases: tuple[str, ...]
    competitor_keywords: tuple[str, ...]
    competitor_tag_values: tuple[str, ...]
    radius_m: int
    competition_scale: float
    competition_soft_limit: int
    validation_competitor_count: int
    target_weights: dict[str, float] = field(default_factory=dict)
    category: str = "local_business"
    examples: tuple[str, ...] = ()


class UnsupportedBusinessTypeError(ValueError):
    def __init__(
        self,
        business_type: str,
        supported_business_types: tuple[str, ...],
        suggestions: tuple[str, ...] = (),
    ) -> None:
        self.business_type = business_type
        self.supported_business_types = supported_business_types
        self.suggestions = suggestions
        super().__init__(
            f"Unsupported business_type: {business_type!r}. "
            f"Supported values: {', '.join(supported_business_types)}"
        )


PICKUP_POINT_WEIGHTS = {
    "residential_score": 0.24,
    "transport_score": 0.19,
    "retail_anchor_score": 0.16,
    "office_score": 0.10,
    "density_score": 0.12,
    "market_validation": 0.10,
    "education_score": 0.05,
    "competition_penalty": -0.20,
    "norm_competition": -0.05,
}

FOOD_SERVICE_WEIGHTS = {
    "traffic_potential": 0.24,
    "retail_anchor_score": 0.21,
    "density_score": 0.16,
    "residential_score": 0.12,
    "office_score": 0.08,
    "market_validation": 0.08,
    "education_score": 0.04,
    "competition_penalty": -0.18,
    "norm_competition": -0.04,
}

CONVENIENCE_RETAIL_WEIGHTS = {
    "residential_score": 0.22,
    "retail_anchor_score": 0.18,
    "transport_score": 0.16,
    "density_score": 0.14,
    "office_score": 0.08,
    "market_validation": 0.09,
    "education_score": 0.04,
    "competition_penalty": -0.17,
    "norm_competition": -0.04,
}

PERSONAL_SERVICE_WEIGHTS = {
    "transport_score": 0.20,
    "residential_score": 0.18,
    "retail_anchor_score": 0.15,
    "density_score": 0.14,
    "office_score": 0.12,
    "market_validation": 0.08,
    "education_score": 0.04,
    "competition_penalty": -0.16,
    "norm_competition": -0.04,
}

DESTINATION_SERVICE_WEIGHTS = {
    "transport_score": 0.22,
    "residential_score": 0.16,
    "office_score": 0.12,
    "retail_anchor_score": 0.12,
    "density_score": 0.12,
    "education_score": 0.08,
    "market_validation": 0.08,
    "competition_penalty": -0.14,
    "norm_competition": -0.03,
}


PICKUP_POINT_PROFILE = BusinessProfile(
    business_type="pickup_point",
    title="Пункт выдачи заказов",
    aliases=(
        "pickup_point",
        "pvz",
        "пвз",
        "пункт выдачи",
        "пункт выдачи заказов",
        "marketplace_pickup",
        "ozon",
        "wb",
        "wildberries",
        "вб",
        "озон",
        "яндекс маркет",
        "yandex market",
        "ям",
    ),
    competitor_keywords=(
        "ozon",
        "озон",
        "wildberries",
        "вайлдберриз",
        "wb",
        "вб",
        "яндекс маркет",
        "yandex market",
        "яндекс доставка",
        "маркет пвз",
        "cdek",
        "сдэк",
        "boxberry",
        "боксберри",
        "pickpoint",
        "pick point",
        "5post",
        "five post",
        "пятерочка доставка",
        "lamoda",
        "ламода",
        "avito",
        "авито",
        "dpd",
        "dhl",
        "пункт выдачи",
        "пвз",
        "parcel locker",
        "постамат",
    ),
    competitor_tag_values=(
        "outpost",
        "parcel_locker",
        "post_office",
        "courier",
        "delivery",
        "logistics",
        "ecommerce",
    ),
    radius_m=500,
    competition_scale=4.0,
    competition_soft_limit=3,
    validation_competitor_count=2,
    target_weights=PICKUP_POINT_WEIGHTS,
    category="marketplace_logistics",
    examples=("Ozon", "Wildberries", "Яндекс Маркет", "СДЭК", "Boxberry"),
)


def _profile(
    business_type: str,
    title: str,
    aliases: tuple[str, ...],
    competitor_keywords: tuple[str, ...],
    competitor_tag_values: tuple[str, ...],
    radius_m: int,
    competition_scale: float,
    competition_soft_limit: int,
    validation_competitor_count: int,
    target_weights: dict[str, float],
    category: str,
    examples: tuple[str, ...] = (),
) -> BusinessProfile:
    return BusinessProfile(
        business_type=business_type,
        title=title,
        aliases=aliases,
        competitor_keywords=competitor_keywords,
        competitor_tag_values=competitor_tag_values,
        radius_m=radius_m,
        competition_scale=competition_scale,
        competition_soft_limit=competition_soft_limit,
        validation_competitor_count=validation_competitor_count,
        target_weights=target_weights,
        category=category,
        examples=examples,
    )


COFFEE_SHOP_PROFILE = _profile(
    "coffee_shop",
    "Кофейня",
    ("coffee_shop", "coffee", "cafe", "кофейня", "кофе", "кофе с собой", "кофеточка"),
    ("coffee", "кофе", "кофейня", "cafe", "espresso", "капучино", "cofix", "one price coffee", "surf coffee"),
    ("cafe", "coffee_shop"),
    350,
    5.0,
    4,
    3,
    FOOD_SERVICE_WEIGHTS,
    "food_service",
    ("кофейня у дома", "кофе с собой", "specialty coffee"),
)

BEER_STORE_PROFILE = _profile(
    "beer_store",
    "Пивной магазин / бар",
    ("beer_store", "draft_beer", "beer", "pub", "bar", "пивнуха", "пиво", "разливное пиво", "пивной магазин"),
    ("beer", "пиво", "разливное", "craft", "крафт", "pub", "bar", "паб", "красное белое", "винлаб"),
    ("alcohol", "beverages", "beer", "bar", "pub"),
    450,
    5.0,
    3,
    2,
    FOOD_SERVICE_WEIGHTS,
    "food_service",
    ("разливное пиво", "крафтовый бар", "алкомаркет"),
)

PHARMACY_PROFILE = _profile(
    "pharmacy",
    "Аптека",
    ("pharmacy", "drugstore", "аптека", "аптечный пункт"),
    ("pharmacy", "drugstore", "аптека", "горздрав", "ригла", "36.6", "столички", "планета здоровья"),
    ("pharmacy",),
    500,
    5.5,
    4,
    3,
    CONVENIENCE_RETAIL_WEIGHTS,
    "health_retail",
    ("сетевые аптеки", "аптечный пункт"),
)

GROCERY_STORE_PROFILE = _profile(
    "grocery_store",
    "Продуктовый магазин",
    ("grocery_store", "grocery", "supermarket", "продукты", "продуктовый", "магазин продуктов"),
    ("grocery", "supermarket", "продукты", "пятерочка", "магнит", "дикси", "вкусвилл", "перекресток"),
    ("supermarket", "convenience", "grocery"),
    450,
    7.0,
    5,
    3,
    CONVENIENCE_RETAIL_WEIGHTS,
    "daily_retail",
    ("магазин у дома", "мини-маркет", "супермаркет"),
)

BAKERY_PROFILE = _profile(
    "bakery",
    "Пекарня",
    ("bakery", "bread", "пекарня", "булочная", "хлеб"),
    ("bakery", "bread", "пекарня", "булочная", "хлеб", "пироги", "выпечка"),
    ("bakery", "confectionery"),
    350,
    5.0,
    4,
    2,
    FOOD_SERVICE_WEIGHTS,
    "food_service",
    ("пекарня", "булочная", "кондитерская"),
)

FAST_FOOD_PROFILE = _profile(
    "fast_food",
    "Фастфуд / шаурма",
    ("fast_food", "shawarma", "шаурма", "бургерная", "пицца", "фастфуд"),
    ("fast_food", "shawarma", "шаурма", "burger", "бургер", "pizza", "пицца", "донер", "kebab"),
    ("fast_food", "food_court"),
    400,
    6.0,
    4,
    3,
    FOOD_SERVICE_WEIGHTS,
    "food_service",
    ("шаурма", "бургерная", "пицца to go"),
)

RESTAURANT_PROFILE = _profile(
    "restaurant",
    "Ресторан / кафе",
    ("restaurant", "ресторан", "кафе", "bistro", "бистро"),
    ("restaurant", "ресторан", "кафе", "bistro", "бистро", "kitchen", "кухня"),
    ("restaurant", "food_court"),
    500,
    6.0,
    4,
    3,
    FOOD_SERVICE_WEIGHTS,
    "food_service",
    ("кафе", "ресторан", "бистро"),
)

BEAUTY_SALON_PROFILE = _profile(
    "beauty_salon",
    "Салон красоты",
    ("beauty_salon", "beauty", "салон красоты", "косметология", "бьюти"),
    ("beauty", "салон красоты", "косметология", "beauty salon", "spa", "бьюти"),
    ("beauty", "cosmetics", "spa"),
    450,
    5.5,
    4,
    3,
    PERSONAL_SERVICE_WEIGHTS,
    "personal_service",
    ("салон красоты", "косметология", "spa"),
)

BARBERSHOP_PROFILE = _profile(
    "barbershop",
    "Барбершоп",
    ("barbershop", "barber", "барбершоп", "парикмахерская мужская"),
    ("barbershop", "barber", "барбершоп", "мужская парикмахерская", "topgun", "oldboy"),
    ("hairdresser",),
    400,
    5.0,
    4,
    2,
    PERSONAL_SERVICE_WEIGHTS,
    "personal_service",
    ("барбершоп", "мужская парикмахерская"),
)

NAIL_SALON_PROFILE = _profile(
    "nail_salon",
    "Маникюр / ногтевая студия",
    ("nail_salon", "nails", "маникюр", "ногти", "ногтевая студия"),
    ("nail", "nails", "маникюр", "ногти", "nail studio", "студия маникюра"),
    ("beauty", "nails"),
    350,
    5.0,
    4,
    2,
    PERSONAL_SERVICE_WEIGHTS,
    "personal_service",
    ("маникюр", "ногтевая студия"),
)

FITNESS_STUDIO_PROFILE = _profile(
    "fitness_studio",
    "Фитнес / спорт-студия",
    ("fitness_studio", "fitness", "gym", "фитнес", "тренажерный зал", "спортзал"),
    ("fitness", "gym", "фитнес", "тренажерный", "спортзал", "yoga", "йога", "pilates", "пилатес"),
    ("fitness_centre", "sports_centre", "gym", "yoga", "pilates"),
    650,
    4.5,
    3,
    2,
    DESTINATION_SERVICE_WEIGHTS,
    "personal_service",
    ("фитнес-студия", "йога", "пилатес", "тренажерный зал"),
)

MEDICAL_CLINIC_PROFILE = _profile(
    "medical_clinic",
    "Медицинская клиника",
    ("medical_clinic", "clinic", "doctors", "медицинская клиника", "медцентр", "клиника"),
    ("clinic", "doctors", "medical", "медцентр", "клиника", "медицинский центр", "лаборатория"),
    ("clinic", "doctors", "laboratory", "medical"),
    700,
    4.0,
    3,
    2,
    DESTINATION_SERVICE_WEIGHTS,
    "medical_service",
    ("медцентр", "частная клиника", "лаборатория"),
)

DENTAL_CLINIC_PROFILE = _profile(
    "dental_clinic",
    "Стоматология",
    ("dental_clinic", "dentist", "dental", "стоматология", "зубная клиника"),
    ("dentist", "dental", "стоматология", "зубная", "ортодонт", "имплантация"),
    ("dentist",),
    650,
    4.0,
    3,
    2,
    DESTINATION_SERVICE_WEIGHTS,
    "medical_service",
    ("стоматология", "ортодонтия", "зубная клиника"),
)

FLOWER_SHOP_PROFILE = _profile(
    "flower_shop",
    "Цветочный магазин",
    ("flower_shop", "florist", "flowers", "цветы", "цветочный"),
    ("florist", "flower", "flowers", "цветы", "букеты", "цветочный"),
    ("florist",),
    400,
    5.5,
    4,
    2,
    CONVENIENCE_RETAIL_WEIGHTS,
    "specialty_retail",
    ("цветы", "букеты", "флористика"),
)

PET_STORE_PROFILE = _profile(
    "pet_store",
    "Зоомагазин",
    ("pet_store", "pet", "зоомагазин", "товары для животных"),
    ("pet", "зоомагазин", "зоотовары", "животных", "four paws", "четыре лапы"),
    ("pet",),
    500,
    4.5,
    3,
    2,
    CONVENIENCE_RETAIL_WEIGHTS,
    "specialty_retail",
    ("зоомагазин", "зоотовары"),
)

CAR_SERVICE_PROFILE = _profile(
    "car_service",
    "Автосервис",
    ("car_service", "auto_service", "car_repair", "автосервис", "шиномонтаж", "автомойка"),
    ("car_repair", "автосервис", "шиномонтаж", "автомойка", "car wash", "мойка", "сто"),
    ("car_repair", "car_wash", "tyres", "auto_parts"),
    800,
    4.0,
    3,
    2,
    DESTINATION_SERVICE_WEIGHTS,
    "auto_service",
    ("автосервис", "шиномонтаж", "автомойка"),
)

DRY_CLEANING_PROFILE = _profile(
    "dry_cleaning",
    "Химчистка / прачечная",
    ("dry_cleaning", "laundry", "химчистка", "прачечная", "ателье чистки"),
    ("dry_cleaning", "laundry", "химчистка", "прачечная", "cleaning", "аквачистка"),
    ("dry_cleaning", "laundry"),
    450,
    4.5,
    3,
    2,
    PERSONAL_SERVICE_WEIGHTS,
    "personal_service",
    ("химчистка", "прачечная"),
)

CHILDREN_EDUCATION_PROFILE = _profile(
    "children_education",
    "Детский центр / образование",
    ("children_education", "kids", "детский центр", "развивашка", "кружки", "образование"),
    ("детский центр", "развивающий", "кружок", "kids", "children", "школа", "садик", "language school"),
    ("kindergarten", "school", "music_school", "language_school", "college"),
    650,
    4.0,
    3,
    2,
    DESTINATION_SERVICE_WEIGHTS,
    "education_service",
    ("детский центр", "языковая школа", "кружки"),
)

RETAIL_PROFILE = _profile(
    "retail",
    "Магазин у дома / розница",
    ("retail", "shop", "store", "магазин", "торговля", "розница", "магазин у дома"),
    ("shop", "store", "магазин", "retail", "розница", "товары", "универсам"),
    ("supermarket", "convenience", "mall", "department_store", "variety_store"),
    450,
    6.0,
    5,
    3,
    CONVENIENCE_RETAIL_WEIGHTS,
    "daily_retail",
    ("магазин у дома", "товары повседневного спроса"),
)


PROFILE_LIST = (
    PICKUP_POINT_PROFILE,
    COFFEE_SHOP_PROFILE,
    BEER_STORE_PROFILE,
    PHARMACY_PROFILE,
    GROCERY_STORE_PROFILE,
    BAKERY_PROFILE,
    FAST_FOOD_PROFILE,
    RESTAURANT_PROFILE,
    BEAUTY_SALON_PROFILE,
    BARBERSHOP_PROFILE,
    NAIL_SALON_PROFILE,
    FITNESS_STUDIO_PROFILE,
    MEDICAL_CLINIC_PROFILE,
    DENTAL_CLINIC_PROFILE,
    FLOWER_SHOP_PROFILE,
    PET_STORE_PROFILE,
    CAR_SERVICE_PROFILE,
    DRY_CLEANING_PROFILE,
    CHILDREN_EDUCATION_PROFILE,
    RETAIL_PROFILE,
)

PROFILES = {profile.business_type: profile for profile in PROFILE_LIST}


def supported_business_types() -> tuple[str, ...]:
    return tuple(profile.business_type for profile in PROFILE_LIST)


def business_type_catalog(profiles: tuple[BusinessProfile, ...] = PROFILE_LIST) -> list[dict[str, object]]:
    return [
        {
            "business_type": profile.business_type,
            "title": profile.title,
            "category": profile.category,
            "aliases": list(profile.aliases),
            "examples": list(profile.examples),
            "radius_m": profile.radius_m,
        }
        for profile in profiles
    ]


def suggest_business_profiles(query: str, limit: int = 5) -> list[dict[str, object]]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return business_type_catalog(PROFILE_LIST[:limit])

    scored_profiles = []
    for profile in PROFILE_LIST:
        score = _profile_match_score(profile, normalized_query)
        if score > 0:
            scored_profiles.append((score, profile))

    scored_profiles.sort(key=lambda item: (-item[0], item[1].business_type))
    return business_type_catalog(tuple(profile for _score, profile in scored_profiles[:limit]))


def get_business_profile(business_type: str) -> BusinessProfile:
    normalized = normalize_text(business_type)
    for profile in PROFILE_LIST:
        normalized_aliases = {normalize_text(alias) for alias in profile.aliases}
        if normalized == profile.business_type or normalized in normalized_aliases:
            return profile
    suggestions = tuple(item["business_type"] for item in suggest_business_profiles(business_type, limit=5))
    raise UnsupportedBusinessTypeError(business_type, supported_business_types(), suggestions)


def _profile_match_score(profile: BusinessProfile, normalized_query: str) -> int:
    fields = [
        profile.business_type,
        profile.title,
        profile.category,
        *profile.aliases,
        *profile.examples,
        *profile.competitor_keywords,
        *profile.competitor_tag_values,
    ]
    normalized_fields = [normalize_text(field) for field in fields]

    score = 0
    for field in normalized_fields:
        if normalized_query == field:
            score = max(score, 100)
        elif normalized_query in field:
            score = max(score, 70)
        elif any(len(token) >= 3 and token in field for token in normalized_query.split()):
            score = max(score, 35)
    return score
