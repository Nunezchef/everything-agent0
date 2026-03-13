from __future__ import annotations

from pathlib import Path

from python.helpers.tool import Tool, Response
from python.helpers.ea0_sync.sync import run_sync
from python.helpers.ea0_sync.learning_v1_process import process_pending_observations_with_agent
from python.helpers.notification import NotificationManager, NotificationType, NotificationPriority
try:
    from python.helpers.extension import clear_extensions_cache
except ImportError:
    def clear_extensions_cache() -> None:
        return None


class Ea0SyncTool(Tool):
    async def execute(self, **kwargs) -> Response:
        action = str(kwargs.get("action") or self.args.get("action") or "sync").strip().lower()
        workspace_raw = kwargs.get("workspace_root") or self.args.get("workspace_root")
        workspace_root = Path(str(workspace_raw)).resolve() if workspace_raw else Path(__file__).resolve().parents[2]
        if action == "learning_process":
            result = await process_pending_observations_with_agent(workspace_root=workspace_root, agent=self.agent)
            return Response(
                message=(
                    "EA0 learning processed: "
                    f"{result['processed_count']} observations, "
                    f"{result['fragment_count']} fragment patterns, "
                    f"{result['solution_count']} solutions"
                ),
                break_loop=False,
                additional=result,
            )
        vendor_raw = Path(str(kwargs.get("vendor_root") or self.args.get("vendor_root") or "usr/everything-claude-code"))
        vendor_root = vendor_raw if vendor_raw.is_absolute() else (workspace_root / vendor_raw).resolve()
        source_sha = str(kwargs.get("source_sha") or self.args.get("source_sha") or "local")

        result = run_sync(vendor_root=vendor_root, workspace_root=workspace_root, source_sha=source_sha)
        if result.success:
            clear_extensions_cache()
        health_status = result.health_report.get("status", "unknown")
        try:
            NotificationManager.send_notification(
                NotificationType.SUCCESS if result.success else NotificationType.ERROR,
                NotificationPriority.NORMAL if result.success else NotificationPriority.HIGH,
                f"EA0 integration {'installed' if result.success else 'install failed'} ({len(result.generated_paths)} files).",
                "EA0 Integration",
                detail=f"health={health_status}, source_sha={source_sha}",
                display_time=5 if result.success else 8,
                group="ea0-install",
            )
        except Exception:
            # Notification requires active AgentContext; keep sync tool usable in tests/CLI paths.
            pass
        return Response(
            message=(
                f"EA0 sync {'succeeded' if result.success else 'failed'}: "
                f"{len(result.generated_paths)} files, manifest={result.manifest_path}, health={health_status}"
            ),
            break_loop=False,
            additional={"success": result.success, "health_report": result.health_report},
        )
