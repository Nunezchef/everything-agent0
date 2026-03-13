from __future__ import annotations

import json
from pathlib import Path

EVENT_TO_POINT = {
    "PreToolUse": "tool_execute_before",
    "PostToolUse": "tool_execute_after",
    "SessionStart": "agent_init",
    "SessionEnd": "message_loop_end",
    "Stop": "message_loop_end",
    "PreCompact": "message_loop_prompts_before",
}

HOOK_POINT_MAP = {
    "pre_prompt": "message_loop_prompts_before",
    "post_prompt": "message_loop_prompts_after",
    "agent_init": "agent_init",
    "message_end": "message_loop_end",
}


def _resolve_point(hook_stem: str) -> str | None:
    for key, point in HOOK_POINT_MAP.items():
        if key in hook_stem:
            return point
    return None


def _extract_command_rules(rules: object) -> list[dict[str, object]]:
    extracted: list[dict[str, object]] = []
    if not isinstance(rules, list):
        return extracted

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        matcher = str(rule.get("matcher") or "*")
        description = str(rule.get("description") or "").strip()
        for hook in rule.get("hooks", []):
            if not isinstance(hook, dict):
                continue
            if hook.get("type") != "command" or not hook.get("command"):
                continue
            extracted.append(
                {
                    "matcher": matcher,
                    "command": str(hook.get("command")),
                    "async": bool(hook.get("async", False)),
                    "timeout": hook.get("timeout"),
                    "description": description,
                }
            )
    return extracted


def _render_rule_bridge(*, event_name: str, vendor_root: Path, rules: list[dict[str, object]]) -> str:
    rules_json = json.dumps(rules, indent=8, sort_keys=True)
    return (
        "from pathlib import Path\n"
        "from python.helpers.extension import Extension\n"
        "from python.helpers.ea0_sync.hook_runtime import run_hook_rules\n\n"
        "class Ea0HookBridge(Extension):\n"
        "    async def execute(self, **kwargs):\n"
        f"        rules = {rules_json}\n"
        "        payload = {\n"
        f"            'event': '{event_name}',\n"
        "            'kwargs': kwargs,\n"
        "            'agent': str(getattr(self.agent, 'agent_name', '')) if self.agent else '',\n"
        "        }\n"
        f"        plugin_root = Path({str(vendor_root)!r})\n"
        "        run_hook_rules(rules=rules, payload=payload, plugin_root=plugin_root)\n"
        "        return None\n"
    )


def transform_hooks(vendor_root: Path, output_root: Path) -> list[str]:
    hooks_root = vendor_root / "hooks"
    generated: list[str] = []

    mapped: dict[str, str] = {}
    unsupported: list[str] = []
    mapped_events: dict[str, str] = {}

    # Primary source: EA0 hooks/hooks.json event configuration.
    config_path = hooks_root / "hooks.json"
    if config_path.is_file():
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        events = cfg.get("hooks", {}) if isinstance(cfg, dict) else {}
        for event_name, rules in events.items():
            point = EVENT_TO_POINT.get(event_name)
            if not point:
                unsupported.append(event_name)
                continue

            command_rules = _extract_command_rules(rules)
            if not command_rules:
                continue

            ext_dir = output_root / "usr" / "extensions" / point
            ext_dir.mkdir(parents=True, exist_ok=True)
            target = ext_dir / f"_80_ea0_{event_name.lower()}.py"
            content = _render_rule_bridge(event_name=event_name, vendor_root=vendor_root, rules=command_rules)
            target.write_text(content, encoding="utf-8")
            rel = str(target.relative_to(output_root)).replace("\\", "/")
            generated.append(rel)
            mapped_events[event_name] = point

    if not hooks_root.is_dir():
        hooks_root = vendor_root / "scripts" / "hooks"
        if not hooks_root.is_dir():
            state_dir = output_root / "usr" / "plugins" / "ea0-integration" / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            report_path = state_dir / "hook_compatibility.json"
            report = {"mapped": mapped, "unsupported": sorted(unsupported), "mapped_events": mapped_events}
            report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            generated.append(str(report_path.relative_to(output_root)).replace("\\", "/"))
            return generated

    # Only use legacy file-based hooks when hooks.json is absent. The structured config
    # is the source of truth when present, and non-hook files like README.md should not
    # be reported as unsupported in that case.
    if not config_path.is_file():
        for hook_file in sorted(hooks_root.rglob("*")):
            if not hook_file.is_file():
                continue

            point = _resolve_point(hook_file.stem.lower())
            if point is None:
                unsupported.append(hook_file.name)
                continue

            ext_dir = output_root / "usr" / "extensions" / point
            ext_dir.mkdir(parents=True, exist_ok=True)

            target = ext_dir / f"_80_ea0_{hook_file.stem.lower()}.py"
            content = (
                "from python.helpers.extension import Extension\n\n"
                "class Ea0HookBridge(Extension):\n"
                "    async def execute(self, **kwargs):\n"
                f"        # Source EA0 hook: {hook_file.name}\n"
                "        # TODO: execute adapted hook semantics.\n"
                "        return None\n"
            )
            target.write_text(content, encoding="utf-8")
            rel = str(target.relative_to(output_root)).replace("\\", "/")
            generated.append(rel)
            mapped[hook_file.name] = point

    state_dir = output_root / "usr" / "plugins" / "ea0-integration" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    report_path = state_dir / "hook_compatibility.json"
    report = {
        "mapped": mapped,
        "unsupported": sorted(unsupported),
        "mapped_events": mapped_events,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    generated.append(str(report_path.relative_to(output_root)).replace("\\", "/"))

    return generated
