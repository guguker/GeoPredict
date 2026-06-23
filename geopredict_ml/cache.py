from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def stable_cache_key(namespace: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{namespace}_{digest[:24]}"


def read_json_cache(cache_dir: str | Path, key: str) -> dict[str, Any] | None:
    path = Path(cache_dir) / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_cache(cache_dir: str | Path, key: str, value: dict[str, Any]) -> Path:
    path = Path(cache_dir) / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
