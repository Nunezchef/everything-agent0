from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from python.helpers.api import ApiHandler, Request, Response
from python.helpers.ecc_sync.sync import run_sync
from python.helpers.ecc_sync.healthcheck import evaluate_workspace_health
from python.helpers.ecc_sync.manifest import read_manifest
from python.helpers.ecc_sync.backup_points import (
    create_backup_point,
    list_backup_points,
    restore_backup_point,
)
from python.helpers.ecc_sync.git_update import update_to_latest, get_repo_info
from python.helpers.ecc_sync.vendor_manager import read_vendor_state
from python.helpers.notification import NotificationManager, NotificationType, NotificationPriority
from python.helpers.extension import clear_extensions_cache


class EccSync(ApiHandler):
    def _notify(self, *, ok: bool, message: str, detail: str = "", group: str = "ecc-install") -> None:
        try:
            NotificationManager.send_notification(
                NotificationType.SUCCESS if ok else NotificationType.ERROR,
                NotificationPriority.NORMAL if ok else NotificationPriority.HIGH,
                message,
                "ECC Integration",
                detail=detail,
                display_time=5 if ok else 8,
                group=group,
            )
        except Exception:
            pass

    def _default_workspace_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _resolve_workspace(self, input: dict) -> Path:
        workspace_raw = input.get("workspace_root")
        if workspace_raw:
            return Path(str(workspace_raw)).resolve()
        return self._default_workspace_root()

    def _resolve_vendor_root(self, input: dict, workspace_root: Path) -> Path:
        raw = Path(str(input.get("vendor_root") or "usr/everything-claude-code"))
        if raw.is_absolute():
            return raw
        return (workspace_root / raw).resolve()

    def _resolve_source_sha(self, input: dict, vendor_root: Path) -> str:
        explicit = str(input.get("source_sha") or "").strip()
        if explicit:
            return explicit
        try:
            info = get_repo_info(vendor_root)
            if info.get("current_sha"):
                return str(info["current_sha"])
        except Exception:
            pass
        return "local"

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = str(input.get("action") or "sync").strip().lower()
        workspace_root = self._resolve_workspace(input)
        vendor_root = self._resolve_vendor_root(input, workspace_root)
        state_dir = workspace_root / "usr" / "plugins" / "ecc-integration" / "state"

        if action == "status":
            manifest = read_manifest(state_dir / "manifest.json")
            vendor_state = read_vendor_state(state_dir / "vendor_state.json")
            repo_info = get_repo_info(vendor_root)
            injection = {
                "system_prompt_extension": (workspace_root / "usr" / "extensions" / "system_prompt" / "_50_ecc_context.py").is_file(),
                "reference_prompt": (workspace_root / "usr" / "prompts" / "fw.ecc.reference.md").is_file(),
                "core_memory": (workspace_root / "usr" / "knowledge" / "core-memories" / "ecc" / "agent0-ecc-integration.md").is_file(),
            }
            return {
                "success": True,
                "health_report": evaluate_workspace_health(workspace_root),
                "manifest": manifest,
                "vendor_state": vendor_state,
                "vendor": repo_info,
                "injection": injection,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        if action == "backup_create":
            source_sha = self._resolve_source_sha(input, vendor_root)
            meta = create_backup_point(workspace_root=workspace_root, source_sha=source_sha)
            self._notify(ok=True, message=f"ECC backup created ({meta['id']}).", group="ecc-backup")
            return {"success": True, "item": meta}

        if action == "backup_list":
            return {"success": True, "items": list_backup_points(workspace_root=workspace_root)}

        if action == "backup_restore":
            backup_id = str(input.get("backup_id") or "").strip()
            if not backup_id:
                return {"success": False, "error": "backup_id is required"}
            result = restore_backup_point(workspace_root=workspace_root, backup_id=backup_id)
            self._notify(ok=True, message=f"ECC backup restored ({backup_id}).", group="ecc-backup")
            return {"success": True, "result": result}

        if action == "update_latest":
            source_sha = self._resolve_source_sha(input, vendor_root)
            backup_meta = None
            if bool(input.get("backup_before_update", False)):
                backup_meta = create_backup_point(workspace_root=workspace_root, source_sha=source_sha)
                self._notify(
                    ok=True,
                    message=f"ECC backup created ({backup_meta['id']}) before update.",
                    group="ecc-backup",
                )
            git_result = update_to_latest(vendor_root)
            if not git_result.get("success", False):
                self._notify(
                    ok=False,
                    message="ECC update from git failed.",
                    detail=str(git_result.get("error", "")),
                    group="ecc-install",
                )
                return {"success": False, "git": git_result}

            result = run_sync(vendor_root=vendor_root, workspace_root=workspace_root, source_sha=source_sha)
            if result.success:
                clear_extensions_cache()
            repo_info = get_repo_info(vendor_root)
            vendor_state = read_vendor_state(state_dir / "vendor_state.json")
            self._notify(
                ok=result.success,
                message=f"ECC updated to latest ({len(result.generated_paths)} files).",
                detail=f"health={result.health_report.get('status', 'unknown')}, source_sha={source_sha}",
                group="ecc-install",
            )
            return {
                "success": result.success,
                "git": git_result,
                "backup": backup_meta,
                "generated_count": len(result.generated_paths),
                "manifest": str(result.manifest_path),
                "health_report": result.health_report,
                "vendor": repo_info,
                "vendor_state": vendor_state,
            }

        # Default and explicit sync action
        source_sha = self._resolve_source_sha(input, vendor_root)
        result = run_sync(vendor_root=vendor_root, workspace_root=workspace_root, source_sha=source_sha)
        if result.success:
            clear_extensions_cache()
        repo_info = get_repo_info(vendor_root)
        vendor_state = read_vendor_state(state_dir / "vendor_state.json")
        self._notify(
            ok=result.success,
            message=f"ECC integration {'installed' if result.success else 'install failed'} ({len(result.generated_paths)} files).",
            detail=f"health={result.health_report.get('status', 'unknown')}, source_sha={source_sha}",
            group="ecc-install",
        )
        return {
            "success": result.success,
            "generated_count": len(result.generated_paths),
            "manifest": str(result.manifest_path),
            "health_report": result.health_report,
            "vendor": repo_info,
            "vendor_state": vendor_state,
        }
