import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


TRANSFORM_HOOKS_PATH = Path("/a0/usr/workdir/Ea0/runtime/python/helpers/ea0_sync/transform_hooks.py")
HOOK_RUNTIME_PATH = Path("/a0/usr/workdir/Ea0/runtime/python/helpers/ea0_sync/hook_runtime.py")
RUNTIME_ROOT = Path("/a0/usr/workdir/Ea0/runtime")

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HookBridgeTest(unittest.TestCase):
    def test_transform_hooks_preserves_rule_semantics(self):
        module = load_module("transform_hooks_module", TRANSFORM_HOOKS_PATH)

        with tempfile.TemporaryDirectory() as vendor_dir, tempfile.TemporaryDirectory() as output_dir:
            vendor_root = Path(vendor_dir)
            output_root = Path(output_dir)
            hooks_dir = vendor_root / "hooks"
            hooks_dir.mkdir(parents=True)
            (hooks_dir / "hooks.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Bash|Write",
                                    "description": "test rule",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": 'echo "sync"',
                                            "timeout": 9,
                                        },
                                        {
                                            "type": "command",
                                            "command": 'echo "async"',
                                            "async": True,
                                            "timeout": 3,
                                        },
                                    ],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            generated = module.transform_hooks(vendor_root, output_root)

            bridge_path = output_root / "usr" / "extensions" / "tool_execute_before" / "_80_ea0_pretooluse.py"
            report_path = output_root / "usr" / "plugins" / "ea0-integration" / "state" / "hook_compatibility.json"

            self.assertIn("usr/extensions/tool_execute_before/_80_ea0_pretooluse.py", generated)
            self.assertIn("usr/plugins/ea0-integration/state/hook_compatibility.json", generated)

            bridge_text = bridge_path.read_text(encoding="utf-8")
            self.assertIn('"matcher": "Bash|Write"', bridge_text)
            self.assertIn('"command": "echo \\"sync\\""', bridge_text)
            self.assertIn('"timeout": 9', bridge_text)
            self.assertIn('"async": true', bridge_text)

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["mapped_events"]["PreToolUse"], "tool_execute_before")
            self.assertEqual(report["unsupported"], [])

    def test_hook_runtime_filters_by_matcher_and_preserves_async(self):
        module = load_module("hook_runtime_module", HOOK_RUNTIME_PATH)

        with tempfile.TemporaryDirectory() as plugin_dir:
            plugin_root = Path(plugin_dir)
            sync_file = plugin_root / "sync.txt"
            async_file = plugin_root / "async.txt"

            rules = [
                {"matcher": "Bash", "command": f"printf sync > {sync_file}", "async": False, "timeout": 5},
                {"matcher": "Write", "command": f"printf async > {async_file}", "async": True, "timeout": 5},
            ]
            payload = {"event": "PreToolUse", "kwargs": {"tool_name": "Bash"}}

            results = module.run_hook_rules(rules=rules, payload=payload, plugin_root=plugin_root)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["matcher"], "Bash")
            self.assertFalse(results[0]["async"])
            self.assertTrue(sync_file.exists())
            self.assertFalse(async_file.exists())

    def test_hook_runtime_uses_rule_timeout(self):
        module = load_module("hook_runtime_module", HOOK_RUNTIME_PATH)

        with tempfile.TemporaryDirectory() as plugin_dir:
            plugin_root = Path(plugin_dir)
            rules = [
                {
                    "matcher": "*",
                    "command": "python3 -c 'import time; time.sleep(0.2)'",
                    "async": False,
                    "timeout": 0.01,
                }
            ]
            payload = {"event": "Stop", "kwargs": {}}

            results = module.run_hook_rules(rules=rules, payload=payload, plugin_root=plugin_root)

            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]["timeout"])
            self.assertIn("timeout after 0.01s", results[0]["error"])


if __name__ == "__main__":
    unittest.main()
