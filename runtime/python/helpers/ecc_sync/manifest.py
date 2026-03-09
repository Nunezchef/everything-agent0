from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_manifest(path: Path, *, source_sha: str, generated_paths: list[str]) -> dict[str, Any]:
    normalized = sorted(set(generated_paths))
    payload: dict[str, Any] = {
        "source_sha": source_sha,
        "generated_paths": normalized,
        "generated_count": len(normalized),
        "checksum": _sha256("\n".join(normalized)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def diff_stale_paths(*, previous: list[str], current: list[str]) -> list[str]:
    prev = set(previous)
    cur = set(current)
    return sorted(prev - cur)
