import asyncio
import importlib.util
import types
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path("/a0/usr/workdir/Ea0/runtime/python/helpers/ea0_sync/learning_scheduler.py")
RUNTIME_ROOT = Path("/a0/usr/workdir/Ea0/runtime")

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))


def load_module():
    fake_task_scheduler = types.ModuleType("python.helpers.task_scheduler")
    fake_task_scheduler.TaskScheduler = FakeTaskScheduler
    fake_task_scheduler.ScheduledTask = FakeScheduledTask

    class FakeTaskSchedule:
        def __init__(self, minute, hour, day, month, weekday):
            self.minute = minute
            self.hour = hour
            self.day = day
            self.month = month
            self.weekday = weekday

    fake_task_scheduler.TaskSchedule = FakeTaskSchedule
    sys.modules["python.helpers.task_scheduler"] = fake_task_scheduler

    spec = importlib.util.spec_from_file_location("learning_scheduler_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeTask:
    def __init__(self, name: str):
        self.name = name
        self.uuid = f"uuid-{name}"


class FakeScheduledTask:
    last_created = None

    @classmethod
    def create(cls, **kwargs):
        cls.last_created = kwargs
        return FakeTask(kwargs["name"])


class FakeScheduler:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
        self.saved = False

    def get_task_by_name(self, name):
        return self.existing if self.existing and self.existing.name == name else None

    async def add_task(self, task):
        self.added.append(task)

    async def save(self):
        self.saved = True


class FakeTaskScheduler:
    current = None

    @classmethod
    def get(cls):
        return cls.current


class LearningSchedulerTest(unittest.TestCase):
    def test_creates_real_scheduled_task_when_missing(self):
        module = load_module()
        fake_scheduler = FakeScheduler()
        FakeTaskScheduler.current = fake_scheduler

        result = asyncio.run(module.ensure_learning_schedule(workspace_root=Path("/tmp/workspace")))

        self.assertEqual(result["status"], "created")
        self.assertEqual(FakeScheduledTask.last_created["name"], module.LEARNING_TASK_NAME)
        self.assertEqual(FakeScheduledTask.last_created["schedule"].minute, "*/15")
        self.assertTrue(fake_scheduler.saved)
        self.assertEqual(len(fake_scheduler.added), 1)
        self.assertIn("ea0_learning_tool", FakeScheduledTask.last_created["prompt"])

    def test_reuses_existing_scheduled_task(self):
        module = load_module()
        existing = FakeTask(module.LEARNING_TASK_NAME)
        fake_scheduler = FakeScheduler(existing=existing)
        FakeTaskScheduler.current = fake_scheduler

        result = asyncio.run(module.ensure_learning_schedule(workspace_root=Path("/tmp/workspace")))

        self.assertEqual(result["status"], "exists")
        self.assertEqual(result["uuid"], existing.uuid)
        self.assertEqual(fake_scheduler.added, [])


if __name__ == "__main__":
    unittest.main()
