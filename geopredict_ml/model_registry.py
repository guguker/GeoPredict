from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .business import BusinessProfile, PROFILE_LIST, get_business_profile
from .model import GradientBoostingRegressorLite, train_reference_model


DEFAULT_MODELS_DIR = Path("models")
MODEL_ARTIFACT_VERSION = "v1"


def model_artifact_name(profile: BusinessProfile, version: str = MODEL_ARTIFACT_VERSION) -> str:
    if profile.business_type == "pickup_point":
        return f"geopredict_pvz_{version}.pkl"
    return f"geopredict_{profile.business_type}_{version}.pkl"


def model_artifact_path(
    profile_or_business_type: BusinessProfile | str,
    models_dir: str | Path = DEFAULT_MODELS_DIR,
    version: str = MODEL_ARTIFACT_VERSION,
) -> Path:
    profile = (
        profile_or_business_type
        if isinstance(profile_or_business_type, BusinessProfile)
        else get_business_profile(profile_or_business_type)
    )
    return Path(models_dir) / model_artifact_name(profile, version=version)


def load_model_for_profile(
    profile: BusinessProfile,
    models_dir: str | Path = DEFAULT_MODELS_DIR,
    version: str = MODEL_ARTIFACT_VERSION,
) -> GradientBoostingRegressorLite | None:
    path = model_artifact_path(profile, models_dir=models_dir, version=version)
    if not path.exists():
        return None
    model = GradientBoostingRegressorLite.load(path)
    _validate_model_profile(model, profile, path)
    return model


def load_explicit_model(path: str | Path, profile: BusinessProfile) -> GradientBoostingRegressorLite:
    model = GradientBoostingRegressorLite.load(path)
    _validate_model_profile(model, profile, Path(path))
    return model


def train_registered_model(profile: BusinessProfile) -> GradientBoostingRegressorLite:
    return train_reference_model(profile)


def train_all_registered_models(
    models_dir: str | Path = DEFAULT_MODELS_DIR,
    version: str = MODEL_ARTIFACT_VERSION,
) -> list[dict[str, Any]]:
    output_dir = Path(models_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []

    for profile in PROFILE_LIST:
        model = train_registered_model(profile)
        path = model_artifact_path(profile, models_dir=output_dir, version=version)
        model.save(path)
        artifacts.append(_artifact_metadata(profile, model, path, version))

    write_model_manifest(artifacts, output_dir / "manifest.json")
    return artifacts


def write_model_manifest(artifacts: list[dict[str, Any]], path: str | Path) -> None:
    manifest = {
        "artifact_version": MODEL_ARTIFACT_VERSION,
        "total_models": len(artifacts),
        "models": artifacts,
    }
    Path(path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _artifact_metadata(
    profile: BusinessProfile,
    model: GradientBoostingRegressorLite,
    path: Path,
    artifact_version: str,
) -> dict[str, Any]:
    return {
        "business_type": profile.business_type,
        "title": profile.title,
        "category": profile.category,
        "artifact_path": str(path),
        "artifact_version": artifact_version,
        "model_type": model.model_type,
        "model_version": model.model_version,
    }


def _validate_model_profile(
    model: GradientBoostingRegressorLite,
    profile: BusinessProfile,
    path: Path,
) -> None:
    artifact_business_type = getattr(model, "business_type", None)
    if artifact_business_type and artifact_business_type != profile.business_type:
        raise ValueError(
            f"Model artifact {path} was trained for {artifact_business_type!r}, "
            f"but request requires {profile.business_type!r}"
        )
