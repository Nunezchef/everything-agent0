from __future__ import annotations

from pathlib import Path
import shutil


def transform_agents(vendor_root: Path, output_root: Path) -> list[str]:
    src_base = vendor_root / "agents"
    dst_base = output_root / "usr" / "agents" / "ecc"
    generated: list[str] = []

    if not src_base.is_dir():
        return generated

    for src_file in sorted(src_base.rglob("*")):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(src_base)
        dst_file = dst_base / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        generated.append(str(dst_file.relative_to(output_root)).replace("\\", "/"))

    return generated
