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
]


def evaluate_health(components: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_COMPONENTS if not bool(components.get(name, False))]
    return {
        "status": "healthy" if not missing else "unhealthy",
        "missing": missing,
    }


def evaluate_workspace_health(workspace_root: Path) -> dict[str, Any]:
    ext_root = workspace_root / "usr" / "extensions"
    has_ecc_hooks = ext_root.is_dir() and any(ext_root.rglob("_80_ecc_*.py"))
    components = {
        "skills": (workspace_root / "usr" / "skills" / "ecc").is_dir(),
        "agents": (workspace_root / "usr" / "agents" / "ecc").is_dir(),
        "commands": (workspace_root / "usr" / "knowledge" / "ecc-commands").is_dir(),
        "hooks": has_ecc_hooks,
        "tools": (workspace_root / "usr" / "plugins" / "ecc-integration" / "tools").is_dir(),
        "core_memories": (workspace_root / "usr" / "knowledge" / "core-memories" / "ecc").is_dir(),
    }
    report = evaluate_health(components)
    report["components"] = components
    return report
