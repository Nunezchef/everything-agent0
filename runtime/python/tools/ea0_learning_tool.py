from __future__ import annotations

from pathlib import Path

from python.helpers.tool import Tool, Response
from python.helpers.ea0_sync.learning_v1_process import process_pending_observations_with_agent


class Ea0LearningTool(Tool):
    async def execute(self, **kwargs) -> Response:
        workspace_raw = kwargs.get("workspace_root") or self.args.get("workspace_root")
        workspace_root = Path(str(workspace_raw)).resolve() if workspace_raw else Path(__file__).resolve().parents[2]
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
