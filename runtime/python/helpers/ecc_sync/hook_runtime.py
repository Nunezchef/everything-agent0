from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
import subprocess
from typing import Any


def _expand_command(command: str, plugin_root: Path) -> str:
    return command.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))


def _json_safe(value: Any, seen: set[int] | None = None) -> Any:
    if seen is None:
        seen = set()

    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    obj_id = id(value)
    if obj_id in seen:
        return "<circular>"

    if isinstance(value, dict):
        seen.add(obj_id)
        return {str(k): _json_safe(v, seen) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        seen.add(obj_id)
        return [_json_safe(v, seen) for v in value]

    if dataclasses.is_dataclass(value):
        seen.add(obj_id)
        return {
            str(field.name): _json_safe(getattr(value, field.name, None), seen)
            for field in dataclasses.fields(value)
        }

    if hasattr(value, "model_dump"):
        try:
            seen.add(obj_id)
            return _json_safe(value.model_dump(), seen)
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        try:
            seen.add(obj_id)
            return {
                str(k): _json_safe(v, seen)
                for k, v in vars(value).items()
                if not str(k).startswith("__")
            }
        except Exception:
            pass

    return str(value)


def run_hook_commands(
    *,
    commands: list[str],
    payload: dict[str, Any],
    plugin_root: Path,
    timeout_seconds: float = 30.0,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    data = json.dumps(_json_safe(payload), ensure_ascii=False)

    for raw in commands:
        command = _expand_command(raw, plugin_root)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                input=data,
                text=True,
                capture_output=True,
                env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root)},
                timeout=timeout_seconds,
            )
            results.append(
                {
                    "command": command,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                }
            )
        except subprocess.TimeoutExpired as e:
            results.append(
                {
                    "command": command,
                    "error": f"timeout after {timeout_seconds}s",
                    "timeout": True,
                    "stdout": e.stdout or "",
                    "stderr": e.stderr or "",
                }
            )
        except Exception as e:
            results.append({"command": command, "error": str(e)})

    return results
