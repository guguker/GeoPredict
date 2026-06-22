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
    target_weights={
        "residential_score": 0.24,
        "transport_score": 0.19,
        "retail_anchor_score": 0.16,
        "office_score": 0.10,
        "density_score": 0.12,
        "market_validation": 0.10,
        "education_score": 0.05,
        "competition_penalty": -0.20,
        "norm_competition": -0.05,
    },
)


RETAIL_PROFILE = BusinessProfile(
    business_type="retail",
    title="Розничная торговля",
    aliases=("retail", "shop", "store", "магазин", "торговля"),
    competitor_keywords=("shop", "store", "магазин", "retail"),
    competitor_tag_values=("supermarket", "convenience", "mall", "department_store"),
    radius_m=450,
    competition_scale=6.0,
    competition_soft_limit=5,
    validation_competitor_count=3,
    target_weights={
        "transport_score": 0.22,
        "retail_anchor_score": 0.20,
        "density_score": 0.18,
        "residential_score": 0.15,
        "office_score": 0.08,
        "market_validation": 0.07,
        "competition_penalty": -0.16,
        "norm_competition": -0.04,
    },
)


PROFILES = {
    PICKUP_POINT_PROFILE.business_type: PICKUP_POINT_PROFILE,
    RETAIL_PROFILE.business_type: RETAIL_PROFILE,
}


def get_business_profile(business_type: str) -> BusinessProfile:
    normalized = normalize_text(business_type)
    for profile in PROFILES.values():
        if normalized == profile.business_type or normalized in profile.aliases:
            return profile
    raise ValueError(f"Unsupported business_type: {business_type!r}")
