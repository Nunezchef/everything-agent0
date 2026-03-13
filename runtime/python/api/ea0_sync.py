from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from python.helpers.api import ApiHandler, Request, Response
from python.helpers.ea0_sync.sync import run_sync
from python.helpers.ea0_sync.healthcheck import evaluate_workspace_health
from python.helpers.ea0_sync.manifest import read_manifest
from python.helpers.ea0_sync.backup_points import (
    create_backup_point,
    list_backup_points,
    restore_backup_point,
)
from python.helpers.ea0_sync.git_update import update_to_latest, get_repo_info
from python.helpers.ea0_sync.vendor_manager import read_vendor_state
from python.helpers.ea0_sync.learning_scheduler import ensure_learning_schedule, LEARNING_TASK_NAME
from python.helpers.ea0_sync.learning_store import learning_state_dir
from python.helpers.ea0_sync.learning_v1_process import process_pending_observations_with_agent
from python.helpers.notification import NotificationManager, NotificationType, NotificationPriority
try:
    from python.helpers.extension import clear_extensions_cache
except ImportError:
    def clear_extensions_cache() -> None:
        return None


class Ea0Sync(ApiHandler):
    def _notify(self, *, ok: bool, message: str, detail: str = "", group: str = "ea0-install") -> None:
        try:
            NotificationManager.send_notification(
                NotificationType.SUCCESS if ok else NotificationType.ERROR,
                NotificationPriority.NORMAL if ok else NotificationPriority.HIGH,
                message,
                "EA0 Integration",
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

    def _learning_status(self, workspace_root: Path) -> dict:
        import json
        from python.helpers.task_scheduler import TaskScheduler

        learning_dir = learning_state_dir(workspace_root)
        status_path = learning_dir / "status.json"
        checkpoints_path = learning_dir / "checkpoints.json"
        observations_path = learning_dir / "observations.jsonl"

        scheduler = TaskScheduler.get()
        task = scheduler.get_task_by_name(LEARNING_TASK_NAME)

        observation_count = 0
        if observations_path.exists():
            with observations_path.open("r", encoding="utf-8") as handle:
                observation_count = sum(1 for line in handle if line.strip())

        checkpoints = json.loads(checkpoints_path.read_text(encoding="utf-8")) if checkpoints_path.exists() else {}
        last_processed = int(checkpoints.get("last_processed_line", 0))
        pending_count = max(0, observation_count - last_processed)

        return {
            "status": json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {},
            "checkpoints": checkpoints,
            "scheduler": {
                "present": task is not None,
                "name": task.name if task else LEARNING_TASK_NAME,
                "uuid": task.uuid if task else "",
                "state": str(task.state) if task else "missing",
                "next_run_minutes": task.get_next_run_minutes() if task else None,
            },
            "observations": {
                "count": observation_count,
                "pending": pending_count,
                "exists": observations_path.exists(),
            },
        }

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = str(input.get("action") or "sync").strip().lower()
        workspace_root = self._resolve_workspace(input)
        vendor_root = self._resolve_vendor_root(input, workspace_root)
        state_dir = workspace_root / "usr" / "plugins" / "ea0-integration" / "state"

        if action == "status":
            manifest = read_manifest(state_dir / "manifest.json")
            vendor_state = read_vendor_state(state_dir / "vendor_state.json")
            repo_info = get_repo_info(vendor_root)
            injection = {
                "system_prompt_extension": (workspace_root / "usr" / "extensions" / "system_prompt" / "_50_ea0_context.py").is_file(),
                "reference_prompt": (workspace_root / "usr" / "prompts" / "fw.ea0.reference.md").is_file(),
                "core_memory": (workspace_root / "usr" / "knowledge" / "core-memories" / "ea0" / "agent0-ea0-integration.md").is_file(),
            }
            learning = self._learning_status(workspace_root)
            return {
                "success": True,
                "health_report": evaluate_workspace_health(workspace_root),
                "manifest": manifest,
                "vendor_state": vendor_state,
                "vendor": repo_info,
                "injection": injection,
                "learning": learning,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        if action == "backup_create":
            source_sha = self._resolve_source_sha(input, vendor_root)
            meta = create_backup_point(workspace_root=workspace_root, source_sha=source_sha)
            self._notify(ok=True, message=f"EA0 backup created ({meta['id']}).", group="ea0-backup")
            return {"success": True, "item": meta}

        if action == "backup_list":
            return {"success": True, "items": list_backup_points(workspace_root=workspace_root)}

        if action == "backup_restore":
            backup_id = str(input.get("backup_id") or "").strip()
            if not backup_id:
                return {"success": False, "error": "backup_id is required"}
            result = restore_backup_point(workspace_root=workspace_root, backup_id=backup_id)
            self._notify(ok=True, message=f"EA0 backup restored ({backup_id}).", group="ea0-backup")
            return {"success": True, "result": result}

        if action == "learning_status":
            return {
                "success": True,
                "learning": self._learning_status(workspace_root),
            }

        if action == "learning_process":
            result = await process_pending_observations_with_agent(workspace_root=workspace_root, agent=self.agent)
            return {"success": True, "learning": result}

        if action == "learning_schedule_ensure":
            result = await ensure_learning_schedule(workspace_root=workspace_root)
            return {"success": True, "learning": result}

        if action == "update_latest":
            source_sha = self._resolve_source_sha(input, vendor_root)
            backup_meta = None
            if bool(input.get("backup_before_update", False)):
                backup_meta = create_backup_point(workspace_root=workspace_root, source_sha=source_sha)
                self._notify(
                    ok=True,
                    message=f"EA0 backup created ({backup_meta['id']}) before update.",
                    group="ea0-backup",
                )
            git_result = update_to_latest(vendor_root)
            if not git_result.get("success", False):
                self._notify(
                    ok=False,
                    message="EA0 update from git failed.",
                    detail=str(git_result.get("error", "")),
                    group="ea0-install",
                )
                return {"success": False, "git": git_result}

            result = run_sync(vendor_root=vendor_root, workspace_root=workspace_root, source_sha=source_sha)
            if result.success:
                clear_extensions_cache()
            repo_info = get_repo_info(vendor_root)
            vendor_state = read_vendor_state(state_dir / "vendor_state.json")
            self._notify(
                ok=result.success,
                message=f"EA0 updated to latest ({len(result.generated_paths)} files).",
                detail=f"health={result.health_report.get('status', 'unknown')}, source_sha={source_sha}",
                group="ea0-install",
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
            message=f"EA0 integration {'installed' if result.success else 'install failed'} ({len(result.generated_paths)} files).",
            detail=f"health={result.health_report.get('status', 'unknown')}, source_sha={source_sha}",
            group="ea0-install",
        )
        return {
            "success": result.success,
            "generated_count": len(result.generated_paths),
            "manifest": str(result.manifest_path),
            "health_report": result.health_report,
            "vendor": repo_info,
            "vendor_state": vendor_state,
        }
