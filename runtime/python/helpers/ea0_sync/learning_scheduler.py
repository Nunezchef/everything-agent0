from __future__ import annotations

from pathlib import Path


LEARNING_TASK_NAME = "ea0-learning-v1"


def _build_prompt(workspace_root: Path) -> str:
    return (
        "Process pending EA0 learning observations for this Agent0 instance. "
        "Use the `ea0_learning_tool` to process observations with "
        f"`workspace_root={workspace_root}` and then stop."
    )


async def ensure_learning_schedule(*, workspace_root: Path) -> dict[str, str]:
    from python.helpers.task_scheduler import TaskScheduler, ScheduledTask, TaskSchedule

    scheduler = TaskScheduler.get()
    existing = scheduler.get_task_by_name(LEARNING_TASK_NAME)
    if existing:
        return {
            "status": "exists",
            "name": LEARNING_TASK_NAME,
            "uuid": existing.uuid,
        }

    schedule = TaskSchedule(minute="*/15", hour="*", day="*", month="*", weekday="*")
    task = ScheduledTask.create(
        name=LEARNING_TASK_NAME,
        system_prompt="You are running a background EA0 continuous-learning maintenance task.",
        prompt=_build_prompt(workspace_root),
        schedule=schedule,
        attachments=[],
        context_id=None,
    )
    await scheduler.add_task(task)
    await scheduler.save()
    return {
        "status": "created",
        "name": LEARNING_TASK_NAME,
        "uuid": task.uuid,
    }
