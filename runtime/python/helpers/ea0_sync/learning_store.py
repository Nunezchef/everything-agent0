from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def learning_state_dir(workspace_root: Path) -> Path:
    return workspace_root / "usr" / "plugins" / "ea0-integration" / "state" / "learning"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_observation(*, workspace_root: Path, observation: dict[str, Any]) -> None:
    state_dir = learning_state_dir(workspace_root)
    state_dir.mkdir(parents=True, exist_ok=True)
    record = dict(observation)
    record.setdefault("recorded_at", _now_iso())
    path = state_dir / "observations.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def read_pending_observations(*, workspace_root: Path) -> tuple[list[dict[str, Any]], int]:
    state_dir = learning_state_dir(workspace_root)
    observations_path = state_dir / "observations.jsonl"
    checkpoints_path = state_dir / "checkpoints.json"

    last_processed = 0
    if checkpoints_path.exists():
        data = json.loads(checkpoints_path.read_text(encoding="utf-8"))
        last_processed = int(data.get("last_processed_line", 0))

    if not observations_path.exists():
        return [], last_processed

    pending: list[dict[str, Any]] = []
    current_line = last_processed
    with observations_path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            current_line = idx
            if idx <= last_processed:
                continue
            stripped = line.strip()
            if not stripped:
                continue
            pending.append(json.loads(stripped))
    return pending, current_line


def write_checkpoints(*, workspace_root: Path, last_processed_line: int, status: str = "ok") -> None:
    state_dir = learning_state_dir(workspace_root)
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_processed_line": last_processed_line,
        "status": status,
        "updated_at": _now_iso(),
    }
    (state_dir / "checkpoints.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_status(*, workspace_root: Path, payload: dict[str, Any]) -> None:
    state_dir = learning_state_dir(workspace_root)
    state_dir.mkdir(parents=True, exist_ok=True)
    data = dict(payload)
    data["updated_at"] = _now_iso()
    (state_dir / "status.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
