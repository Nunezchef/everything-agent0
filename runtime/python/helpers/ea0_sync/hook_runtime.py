from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from python.helpers.ea0_sync.learning_store import append_observation


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


def _extract_tool_names(payload: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    kwargs = payload.get("kwargs")
    if isinstance(kwargs, dict):
        for key in ("tool_name", "tool", "name", "current_tool", "matcher"):
            value = kwargs.get(key)
            if isinstance(value, str) and value.strip():
                names.add(value.strip())
    for key in ("tool_name", "tool", "name", "event"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            names.add(value.strip())
    return names


def _matches_matcher(matcher: str, payload: dict[str, Any]) -> bool:
    normalized = (matcher or "*").strip()
    if not normalized or normalized == "*":
        return True

    candidates = {name.lower() for name in _extract_tool_names(payload)}
    if not candidates:
        return False

    options = {part.strip().lower() for part in normalized.split("|") if part.strip()}
    if "*" in options:
        return True
    return bool(candidates & options)


def _run_sync_command(command: str, *, payload_json: str, plugin_root: Path, timeout_seconds: float) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            input=payload_json,
            text=True,
            capture_output=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root)},
            timeout=timeout_seconds,
        )
        return {
            "command": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "command": command,
            "error": f"timeout after {timeout_seconds}s",
            "timeout": True,
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
        }
    except Exception as e:
        return {"command": command, "error": str(e), "timeout": False}


def _run_async_command(command: str, *, payload_json: str, plugin_root: Path) -> dict[str, Any]:
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root)},
        )
        if proc.stdin:
            proc.stdin.write(payload_json)
            proc.stdin.close()
        return {
            "command": command,
            "async": True,
            "pid": proc.pid,
            "returncode": None,
            "timeout": False,
        }
    except Exception as e:
        return {"command": command, "async": True, "error": str(e), "timeout": False}


def run_hook_rules(
    *,
    rules: list[dict[str, Any]],
    payload: dict[str, Any],
    plugin_root: Path,
    default_timeout_seconds: float = 30.0,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    payload_json = json.dumps(_json_safe(payload), ensure_ascii=False)

    for rule in rules:
        matcher = str(rule.get("matcher") or "*")
        if not _matches_matcher(matcher, payload):
            continue

        command = _expand_command(str(rule.get("command") or ""), plugin_root)
        if not command:
            continue

        timeout_seconds = float(rule.get("timeout") or default_timeout_seconds)
        is_async = bool(rule.get("async", False))
        result = (
            _run_async_command(command, payload_json=payload_json, plugin_root=plugin_root)
            if is_async
            else _run_sync_command(
                command,
                payload_json=payload_json,
                plugin_root=plugin_root,
                timeout_seconds=timeout_seconds,
            )
        )
        result["matcher"] = matcher
        result["async"] = is_async
        result["rule_timeout"] = timeout_seconds
        results.append(result)

        try:
            event_name = str(payload.get("event") or "")
            if event_name in {"PostToolUse", "Stop", "SessionEnd"}:
                kwargs = payload.get("kwargs", {}) if isinstance(payload.get("kwargs"), dict) else {}
                summary = str(kwargs.get("summary") or kwargs.get("message") or command).strip()
                observation = {
                    "event": event_name,
                    "tool_name": str(kwargs.get("tool_name") or kwargs.get("tool") or ""),
                    "success": (result.get("returncode", 0) == 0) if not is_async else True,
                    "project_id": str(kwargs.get("project_id") or ""),
                    "project_name": str(kwargs.get("project_name") or ""),
                    "session_id": str(kwargs.get("session_id") or ""),
                    "summary": summary[:500],
                    "source_agent": str(payload.get("agent") or ""),
                }
                workspace_root = plugin_root if (plugin_root / "usr").is_dir() else plugin_root.parents[2]
                append_observation(workspace_root=workspace_root, observation=observation)
        except Exception:
            pass

    return results


def run_hook_commands(
    *,
    commands: list[str],
    payload: dict[str, Any],
    plugin_root: Path,
    timeout_seconds: float = 30.0,
) -> list[dict[str, Any]]:
    rules = [
        {"matcher": "*", "command": command, "async": False, "timeout": timeout_seconds}
        for command in commands
    ]
    return run_hook_rules(
        rules=rules,
        payload=payload,
        plugin_root=plugin_root,
        default_timeout_seconds=timeout_seconds,
    )
