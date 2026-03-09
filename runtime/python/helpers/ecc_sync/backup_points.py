from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

ECC_PATHS = [
    "usr/skills/ecc",
    "usr/agents/ecc",
    "usr/knowledge/ecc-commands",
    "usr/knowledge/core-memories/ecc",
    "usr/plugins/ecc-integration/state",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _backups_root(workspace_root: Path) -> Path:
    return workspace_root / "usr" / "plugins" / "ecc-integration" / "backups"


def create_backup_point(*, workspace_root: Path, source_sha: str) -> dict[str, Any]:
    backup_id = _utc_now()
    root = _backups_root(workspace_root)
    target = root / backup_id
    target.mkdir(parents=True, exist_ok=True)

    included: list[str] = []
    for rel in ECC_PATHS:
        src = workspace_root / rel
        if not src.exists():
            continue
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            included.append(rel + "/")
        else:
            shutil.copy2(src, dst)
            included.append(rel)

    meta = {
        "id": backup_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_sha": source_sha,
        "paths": included,
    }
    (target / "metadata.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def list_backup_points(*, workspace_root: Path) -> list[dict[str, Any]]:
    root = _backups_root(workspace_root)
    if not root.exists():
        return []

    items: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        meta = entry / "metadata.json"
        if not meta.is_file():
            continue
        items.append(json.loads(meta.read_text(encoding="utf-8")))
    return items


def restore_backup_point(*, workspace_root: Path, backup_id: str) -> dict[str, Any]:
    backup_root = _backups_root(workspace_root) / backup_id
    if not backup_root.is_dir():
        raise FileNotFoundError(f"Backup not found: {backup_id}")

    metadata_path = backup_root / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Backup metadata missing: {backup_id}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="ecc_restore_") as td:
        stage = Path(td) / "restore"
        shutil.copytree(backup_root, stage, dirs_exist_ok=True)

        for rel in ECC_PATHS:
            dst = workspace_root / rel
            if dst.is_file():
                dst.unlink()
            elif dst.is_dir():
                shutil.rmtree(dst)

        for rel in ECC_PATHS:
            src = stage / rel
            if not src.exists():
                continue
            dst = workspace_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    return {"ok": True, "id": backup_id, "source_sha": metadata.get("source_sha", "")}
