import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path("/a0/usr/workdir/Ea0/runtime/python/helpers/ea0_sync/transform_skills.py")


def load_transform_skills_module():
    spec = importlib.util.spec_from_file_location("transform_skills_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TransformSkillsTest(unittest.TestCase):
    def test_normalizes_known_ecc_references_and_emits_registry(self):
        module = load_transform_skills_module()

        with tempfile.TemporaryDirectory() as vendor_dir, tempfile.TemporaryDirectory() as output_dir:
            vendor_root = Path(vendor_dir)
            output_root = Path(output_dir)
            skill_dir = vendor_root / "skills" / "continuous-learning"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                """---
name: continuous-learning
description: Automatically extract reusable patterns from Claude Code sessions.
origin: ECC
---

# Continuous Learning

Review `~/.claude/skills/learned/`.

Add to your `~/.claude/settings.json`.

Runs after Claude Code sessions.
""",
                encoding="utf-8",
            )

            generated = module.transform_skills(vendor_root, output_root)

            skill_path = output_root / "usr" / "skills" / "ea0" / "continuous-learning" / "SKILL.md"
            registry_path = output_root / "usr" / "plugins" / "ea0-integration" / "state" / "skills.json"

            self.assertIn("usr/skills/ea0/continuous-learning/SKILL.md", generated)
            self.assertIn("usr/plugins/ea0-integration/state/skills.json", generated)

            normalized = skill_path.read_text(encoding="utf-8")
            self.assertIn("Agent0 with EA0 integration sessions", normalized)
            self.assertIn("`usr/skills/ea0/learned/`", normalized)
            self.assertIn("Agent0 settings or EA0 plugin configuration", normalized)
            self.assertNotIn("~/.claude/skills/learned/", normalized)
            self.assertNotIn("~/.claude/settings.json", normalized)
            self.assertNotIn("Claude Code sessions", normalized)

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(len(registry["skills"]), 1)
            entry = registry["skills"][0]
            self.assertEqual(entry["source"], "skills/continuous-learning/SKILL.md")
            self.assertGreaterEqual(entry["rewrites"], 3)
            self.assertEqual(entry["warnings"], [])

    def test_records_warnings_for_unresolved_claude_specific_state(self):
        module = load_transform_skills_module()

        with tempfile.TemporaryDirectory() as vendor_dir, tempfile.TemporaryDirectory() as output_dir:
            vendor_root = Path(vendor_dir)
            output_root = Path(output_dir)
            skill_dir = vendor_root / "skills" / "continuous-learning-v2"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                """---
name: continuous-learning-v2
description: Instinct-based learning system.
origin: ECC
---

# Continuous Learning v2

Installed as a plugin via `${CLAUDE_PLUGIN_ROOT}/skills/continuous-learning-v2/hooks/observe.sh`.

Stores instincts in `~/.claude/homunculus/`.
""",
                encoding="utf-8",
            )

            generated = module.transform_skills(vendor_root, output_root)

            self.assertIn("usr/skills/ea0/continuous-learning-v2/SKILL.md", generated)
            registry_path = output_root / "usr" / "plugins" / "ea0-integration" / "state" / "skills.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["skills"][0]
            self.assertGreaterEqual(entry["rewrites"], 1)
            self.assertIn("claude_state_path:~/.claude/homunculus/", entry["warnings"])

            normalized = (
                output_root / "usr" / "skills" / "ea0" / "continuous-learning-v2" / "SKILL.md"
            ).read_text(encoding="utf-8")
            self.assertIn("`usr/skills/ea0/continuous-learning-v2/hooks/observe.sh`", normalized)
            self.assertIn("`~/.claude/homunculus/`", normalized)


if __name__ == "__main__":
    unittest.main()
