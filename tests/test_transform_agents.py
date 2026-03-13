import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path("/a0/usr/workdir/Ea0/runtime/python/helpers/ea0_sync/transform_agents.py")


def load_transform_agents_module():
    spec = importlib.util.spec_from_file_location("transform_agents_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TransformAgentsTest(unittest.TestCase):
    def test_transforms_ecc_markdown_agents_into_agent0_directories(self):
        module = load_transform_agents_module()

        with tempfile.TemporaryDirectory() as vendor_dir, tempfile.TemporaryDirectory() as output_dir:
            vendor_root = Path(vendor_dir)
            output_root = Path(output_dir)

            agents_dir = vendor_root / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "planner.md").write_text(
                """---
name: planner
description: Expert planning specialist for complex features and refactoring.
tools: ["Read", "Grep", "Glob"]
model: opus
---

# Planner

You are an expert planning specialist focused on creating comprehensive plans.
""",
                encoding="utf-8",
            )

            generated = module.transform_agents(vendor_root, output_root)

            agent_json_path = output_root / "usr" / "agents" / "ea0-planner" / "agent.json"
            context_path = output_root / "usr" / "agents" / "ea0-planner" / "_context.md"
            registry_path = output_root / "usr" / "plugins" / "ea0-integration" / "state" / "agents.json"

            self.assertIn("usr/agents/ea0-planner/agent.json", generated)
            self.assertIn("usr/agents/ea0-planner/_context.md", generated)
            self.assertIn("usr/plugins/ea0-integration/state/agents.json", generated)

            agent_json = json.loads(agent_json_path.read_text(encoding="utf-8"))
            self.assertEqual(agent_json["title"], "EA0 Planner")
            self.assertEqual(
                agent_json["description"],
                "Expert planning specialist for complex features and refactoring.",
            )
            self.assertEqual(agent_json["context"], "")
            self.assertTrue(agent_json["enabled"])

            context = context_path.read_text(encoding="utf-8")
            self.assertIn("# Planner", context)
            self.assertIn("## Agent0 Compatibility", context)
            self.assertIn("Original ECC model: `opus`", context)
            self.assertIn("Original ECC tools: `Read`, `Grep`, `Glob`", context)
            self.assertIn("Agent0 capability mapping: `filesystem-read-write`, `search`", context)
            self.assertIn("You are an expert planning specialist", context)

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(len(registry["agents"]), 1)
            entry = registry["agents"][0]
            self.assertEqual(entry["source"], "agents/planner.md")
            self.assertEqual(entry["ecc_name"], "planner")
            self.assertEqual(entry["generated_name"], "ea0-planner")
            self.assertEqual(entry["ecc_model"], "opus")
            self.assertEqual(entry["ecc_tools"], ["Read", "Grep", "Glob"])
            self.assertEqual(entry["mapped_capabilities"], ["filesystem-read-write", "search"])
            self.assertEqual(entry["warnings"], [])

    def test_handles_missing_frontmatter_with_warning(self):
        module = load_transform_agents_module()

        with tempfile.TemporaryDirectory() as vendor_dir, tempfile.TemporaryDirectory() as output_dir:
            vendor_root = Path(vendor_dir)
            output_root = Path(output_dir)

            agents_dir = vendor_root / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "code-reviewer.md").write_text(
                """# Code Reviewer

Review code carefully.
""",
                encoding="utf-8",
            )

            generated = module.transform_agents(vendor_root, output_root)

            self.assertIn("usr/agents/ea0-code-reviewer/agent.json", generated)
            registry_path = output_root / "usr" / "plugins" / "ea0-integration" / "state" / "agents.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["agents"][0]
            self.assertEqual(entry["generated_name"], "ea0-code-reviewer")
            self.assertTrue(entry["warnings"])


if __name__ == "__main__":
    unittest.main()
