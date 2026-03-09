from __future__ import annotations

from pathlib import Path

from python.helpers.tool import Tool, Response
from python.helpers.ecc_sync.sync import run_sync
from python.helpers.notification import NotificationManager, NotificationType, NotificationPriority
from python.helpers.extension import clear_extensions_cache


class EccSyncTool(Tool):
    async def execute(self, **kwargs) -> Response:
        workspace_raw = kwargs.get("workspace_root") or self.args.get("workspace_root")
        workspace_root = Path(str(workspace_raw)).resolve() if workspace_raw else Path(__file__).resolve().parents[2]
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
                f"ECC integration {'installed' if result.success else 'install failed'} ({len(result.generated_paths)} files).",
                "ECC Integration",
                detail=f"health={health_status}, source_sha={source_sha}",
                display_time=5 if result.success else 8,
                group="ecc-install",
            )
        except Exception:
            # Notification requires active AgentContext; keep sync tool usable in tests/CLI paths.
            pass
        return Response(
            message=(
                f"ECC sync {'succeeded' if result.success else 'failed'}: "
                f"{len(result.generated_paths)} files, manifest={result.manifest_path}, health={health_status}"
            ),
            break_loop=False,
            additional={"success": result.success, "health_report": result.health_report},
        )
