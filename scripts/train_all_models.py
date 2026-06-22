from __future__ import annotations

import argparse
import json

from geopredict_ml.model_registry import train_all_registered_models


def main() -> None:
    parser = argparse.ArgumentParser(description="Train all registered GeoPredict business models.")
    parser.add_argument("--models-dir", default="models", help="Directory for model artifacts.")
    args = parser.parse_args()

    artifacts = train_all_registered_models(args.models_dir)
    print(json.dumps({"total_models": len(artifacts), "models": artifacts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
