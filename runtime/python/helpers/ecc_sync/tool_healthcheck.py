from __future__ import annotations

from pathlib import Path


def check_tool_files_exist(tools_root: Path) -> bool:
    if not tools_root.is_dir():
        return False
    return any(p.is_file() for p in tools_root.rglob("*"))
