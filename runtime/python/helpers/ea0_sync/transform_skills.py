from __future__ import annotations

import json
from pathlib import Path
import shutil


SAFE_REPLACEMENTS = [
    ("Claude Code sessions", "Agent0 with EA0 integration sessions"),
    ("Claude Code session", "Agent0 with EA0 integration session"),
    ("Claude Code", "Agent0 with EA0 integration"),
    ("`~/.claude/skills/learned/`", "`usr/skills/ea0/learned/`"),
    ("~/.claude/skills/learned/", "usr/skills/ea0/learned/"),
    ("`~/.claude/settings.json`", "Agent0 settings or EA0 plugin configuration"),
    ("~/.claude/settings.json", "Agent0 settings or EA0 plugin configuration"),
    ("`${CLAUDE_PLUGIN_ROOT}/skills/", "`usr/skills/ea0/"),
    ("${CLAUDE_PLUGIN_ROOT}/skills/", "usr/skills/ea0/"),
]

WARNING_PATTERNS = {
    "~/.claude/homunculus/": "claude_state_path:~/.claude/homunculus/",
}


def _normalize_skill_text(text: str) -> tuple[str, int, list[str]]:
    rewrites = 0
    normalized = text

    for source, target in SAFE_REPLACEMENTS:
        count = normalized.count(source)
        if count:
            normalized = normalized.replace(source, target)
            rewrites += count

    warnings = [warning for needle, warning in WARNING_PATTERNS.items() if needle in normalized]
    return normalized, rewrites, warnings


def transform_skills(vendor_root: Path, output_root: Path) -> list[str]:
    src_base = vendor_root / "skills"
    dst_base = output_root / "usr" / "skills" / "ea0"
    generated: list[str] = []
    registry_entries: list[dict[str, object]] = []

    if not src_base.is_dir():
        return generated

    for skill_md in sorted(src_base.rglob("SKILL.md")):
        skill_dir = skill_md.parent
        rel = skill_dir.relative_to(src_base)
        target_dir = dst_base / rel
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(skill_dir, target_dir)

        skill_target = target_dir / "SKILL.md"
        rewrites = 0
        warnings: list[str] = []
        if skill_target.exists():
            normalized, rewrites, warnings = _normalize_skill_text(skill_target.read_text(encoding="utf-8"))
            skill_target.write_text(normalized, encoding="utf-8")

        for file_path in sorted(target_dir.rglob("*")):
            if file_path.is_file():
                generated.append(str(file_path.relative_to(output_root)).replace("\\", "/"))

        registry_entries.append(
            {
                "source": str(skill_md.relative_to(vendor_root)).replace("\\", "/"),
                "generated_dir": str(target_dir.relative_to(output_root)).replace("\\", "/"),
                "rewrites": rewrites,
                "warnings": warnings,
            }
        )

    state_dir = output_root / "usr" / "plugins" / "ea0-integration" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    registry_path = state_dir / "skills.json"
    registry_path.write_text(
        json.dumps({"skills": registry_entries}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    generated.append(str(registry_path.relative_to(output_root)).replace("\\", "/"))

    return generated
