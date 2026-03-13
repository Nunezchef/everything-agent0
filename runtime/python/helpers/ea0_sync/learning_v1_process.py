from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from python.helpers.ea0_sync.learning_store import (
    read_pending_observations,
    write_checkpoints,
    write_status,
)


def _scope_for_observation(observation: dict[str, Any]) -> str:
    return "project" if observation.get("project_id") else "global"


def _group_observations(observations: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for obs in observations:
        project_id = str(obs.get("project_id") or "global")
        summary = str(obs.get("summary") or "").strip()
        if not summary:
            continue
        grouped.setdefault((project_id, summary), []).append(obs)
    return grouped


async def process_pending_observations(
    *,
    workspace_root: Path,
    fragment_memory: Any,
    solution_memory: Any,
) -> dict[str, Any]:
    observations, last_line = read_pending_observations(workspace_root=workspace_root)
    grouped = _group_observations(observations)

    fragment_count = 0
    solution_count = 0
    processed_count = len(observations)

    for (_project_id, summary), items in grouped.items():
        first = items[0]
        scope = _scope_for_observation(first)
        metadata = {
            "source": "ea0-learning-v1",
            "scope": scope,
            "project_id": first.get("project_id", ""),
            "project_name": first.get("project_name", ""),
            "confidence": min(0.4 + 0.15 * len(items), 0.95),
            "evidence_count": len(items),
            "event": first.get("event", ""),
        }
        fragment_text = (
            f"# Learned Pattern\n\n"
            f"{summary}\n\n"
            f"Evidence count: {len(items)}\n"
            f"Scope: {scope}\n"
        )
        await fragment_memory.insert_text(fragment_text, metadata={**metadata, "area": "fragments"})
        fragment_count += 1

        successful = [item for item in items if bool(item.get("success"))]
        if successful and any("resolved" in str(item.get("summary", "")).lower() for item in successful):
            solution_text = (
                f"# Problem\n"
                f"Repeated workflow issue in project `{first.get('project_name') or first.get('project_id') or 'global'}`\n\n"
                f"# Solution\n"
                f"{summary}\n"
            )
            await solution_memory.insert_text(solution_text, metadata={**metadata, "area": "solutions"})
            solution_count += 1

    write_checkpoints(workspace_root=workspace_root, last_processed_line=last_line, status="ok")
    result = {
        "processed_count": processed_count,
        "fragment_count": fragment_count,
        "solution_count": solution_count,
    }
    write_status(workspace_root=workspace_root, payload=result)
    return result


async def process_pending_observations_with_agent(*, workspace_root: Path, agent: Any) -> dict[str, Any]:
    from python.helpers.memory import Memory

    db = await Memory.get(agent)
    return await process_pending_observations(
        workspace_root=workspace_root,
        fragment_memory=db,
        solution_memory=db,
    )
