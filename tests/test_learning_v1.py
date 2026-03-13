import asyncio
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


STORE_PATH = Path("/a0/usr/workdir/Ea0/runtime/python/helpers/ea0_sync/learning_store.py")
PROCESS_PATH = Path("/a0/usr/workdir/Ea0/runtime/python/helpers/ea0_sync/learning_v1_process.py")
RUNTIME_ROOT = Path("/a0/usr/workdir/Ea0/runtime")

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeMemory:
    def __init__(self):
        self.entries = []

    async def insert_text(self, text, metadata=None):
        self.entries.append((text, metadata or {}))
        return f"id-{len(self.entries)}"


class LearningV1Test(unittest.TestCase):
    def test_append_observation_and_read_pending(self):
        store = load_module("learning_store_module", STORE_PATH)

        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            observation = {
                "event": "PostToolUse",
                "tool_name": "Bash",
                "success": True,
                "project_id": "proj-1",
                "project_name": "demo",
                "session_id": "sess-1",
                "summary": "Ran focused tests successfully",
            }
            store.append_observation(workspace_root=workspace_root, observation=observation)

            observations, last_line = store.read_pending_observations(workspace_root=workspace_root)
            self.assertEqual(len(observations), 1)
            self.assertEqual(observations[0]["event"], "PostToolUse")
            self.assertEqual(observations[0]["summary"], "Ran focused tests successfully")
            self.assertEqual(last_line, 1)

    def test_process_pending_observations_writes_fragment_and_solution_memories(self):
        process = load_module("learning_v1_process_module", PROCESS_PATH)

        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            observations = [
                {
                    "event": "PostToolUse",
                    "tool_name": "Bash",
                    "success": True,
                    "project_id": "proj-1",
                    "project_name": "demo",
                    "session_id": "sess-1",
                    "summary": "Run focused tests before full suite",
                },
                {
                    "event": "PostToolUse",
                    "tool_name": "Bash",
                    "success": True,
                    "project_id": "proj-1",
                    "project_name": "demo",
                    "session_id": "sess-1",
                    "summary": "Run focused tests before full suite",
                },
                {
                    "event": "Stop",
                    "tool_name": "Bash",
                    "success": True,
                    "project_id": "proj-1",
                    "project_name": "demo",
                    "session_id": "sess-1",
                    "summary": "Resolved failing build by running focused tests first",
                },
            ]

            state_dir = workspace_root / "usr" / "plugins" / "ea0-integration" / "state" / "learning"
            state_dir.mkdir(parents=True, exist_ok=True)
            obs_path = state_dir / "observations.jsonl"
            obs_path.write_text("".join(json.dumps(item) + "\n" for item in observations), encoding="utf-8")

            fragment_memory = FakeMemory()
            solution_memory = FakeMemory()

            result = asyncio.run(
                process.process_pending_observations(
                    workspace_root=workspace_root,
                    fragment_memory=fragment_memory,
                    solution_memory=solution_memory,
                )
            )

            self.assertEqual(result["processed_count"], 3)
            self.assertGreaterEqual(result["fragment_count"], 1)
            self.assertGreaterEqual(result["solution_count"], 1)
            self.assertTrue(fragment_memory.entries)
            self.assertTrue(solution_memory.entries)
            self.assertEqual(fragment_memory.entries[0][1]["source"], "ea0-learning-v1")
            self.assertEqual(fragment_memory.entries[0][1]["scope"], "project")
            self.assertEqual(fragment_memory.entries[0][1]["project_id"], "proj-1")

            checkpoints = json.loads((state_dir / "checkpoints.json").read_text(encoding="utf-8"))
            self.assertEqual(checkpoints["last_processed_line"], 3)


if __name__ == "__main__":
    unittest.main()
