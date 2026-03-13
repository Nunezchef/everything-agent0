from __future__ import annotations

from pathlib import Path
from typing import Mapping, Any

REQUIRED_COMPONENTS = [
    "skills",
    "agents",
    "commands",
    "hooks",
    "tools",
    "core_memories",
    "learning",
]


def evaluate_health(components: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_COMPONENTS if not bool(components.get(name, False))]
    return {
        "status": "healthy" if not missing else "unhealthy",
        "missing": missing,
    }


def evaluate_workspace_health(workspace_root: Path) -> dict[str, Any]:
    ext_root = workspace_root / "usr" / "extensions"
    has_ea0_hooks = ext_root.is_dir() and any(ext_root.rglob("_80_ea0_*.py"))
    learning_dir = workspace_root / "usr" / "plugins" / "ea0-integration" / "state" / "learning"
    components = {
        "skills": (workspace_root / "usr" / "skills" / "ea0").is_dir(),
        "agents": (workspace_root / "usr" / "agents" / "ea0").is_dir(),
        "commands": (workspace_root / "usr" / "knowledge" / "ea0-commands").is_dir(),
        "hooks": has_ea0_hooks,
        "tools": (workspace_root / "usr" / "plugins" / "ea0-integration" / "tools").is_dir(),
        "core_memories": (workspace_root / "usr" / "knowledge" / "core-memories" / "ea0").is_dir(),
        "learning": learning_dir.is_dir(),
    }
    report = evaluate_health(components)
    report["components"] = components
    return report
