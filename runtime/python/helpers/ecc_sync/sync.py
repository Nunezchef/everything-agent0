from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile

from python.helpers.ecc_sync.manifest import write_manifest, read_manifest, diff_stale_paths
from python.helpers.ecc_sync.vendor_manager import write_vendor_state
from python.helpers.ecc_sync.transform_skills import transform_skills
from python.helpers.ecc_sync.transform_agents import transform_agents
from python.helpers.ecc_sync.transform_commands import transform_commands
from python.helpers.ecc_sync.transform_hooks import transform_hooks
from python.helpers.ecc_sync.transform_core_memories import transform_core_memories
from python.helpers.ecc_sync.transform_ecosystem_tools import transform_ecosystem_tools
from python.helpers.ecc_sync.healthcheck import evaluate_workspace_health


@dataclass(slots=True)
class SyncResult:
    success: bool
    generated_paths: list[str]
    manifest_path: Path
    health_report: dict


def run_sync(*, vendor_root: Path, workspace_root: Path, source_sha: str) -> SyncResult:
    manifest_path = workspace_root / "usr" / "plugins" / "ecc-integration" / "state" / "manifest.json"
    previous_manifest = read_manifest(manifest_path)
    previous_generated = previous_manifest.get("generated_paths", []) if isinstance(previous_manifest, dict) else []

    with tempfile.TemporaryDirectory(prefix="ecc_sync_") as td:
        stage_root = Path(td)

        generated: list[str] = []
        generated += transform_skills(vendor_root, stage_root)
        generated += transform_agents(vendor_root, stage_root)
        generated += transform_commands(vendor_root, stage_root)
        generated += transform_hooks(vendor_root, stage_root)
        generated += transform_core_memories(vendor_root, stage_root)
        generated += transform_ecosystem_tools(vendor_root, stage_root)

        state_dir = stage_root / "usr" / "plugins" / "ecc-integration" / "state"
        manifest_path_stage = state_dir / "manifest.json"
        write_manifest(manifest_path_stage, source_sha=source_sha, generated_paths=generated)
        write_vendor_state(state_dir / "vendor_state.json", source=str(vendor_root), commit_sha=source_sha)

        # Remove only stale files from previous ECC-generated manifest, preserving unrelated usr content.
        stale_paths = diff_stale_paths(previous=previous_generated, current=generated)
        for rel in stale_paths:
            target = workspace_root / rel
            if target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)

        src_usr = stage_root / "usr"
        if src_usr.exists():
            dst_usr = workspace_root / "usr"
            dst_usr.mkdir(parents=True, exist_ok=True)
            for src_file in src_usr.rglob("*"):
                if not src_file.is_file():
                    continue
                rel = src_file.relative_to(src_usr)
                dst_file = dst_usr / rel
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)

    health_report = evaluate_workspace_health(workspace_root)
    return SyncResult(
        success=manifest_path.exists(),
        generated_paths=generated,
        manifest_path=manifest_path,
        health_report=health_report,
    )
