from __future__ import annotations

from pathlib import Path
import shutil


def transform_skills(vendor_root: Path, output_root: Path) -> list[str]:
    src_base = vendor_root / "skills"
    dst_base = output_root / "usr" / "skills" / "ecc"
    generated: list[str] = []

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

        for file_path in sorted(target_dir.rglob("*")):
            if file_path.is_file():
                generated.append(str(file_path.relative_to(output_root)).replace("\\", "/"))

    return generated
