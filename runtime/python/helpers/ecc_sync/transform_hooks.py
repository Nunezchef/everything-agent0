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


def transform_hooks(vendor_root: Path, output_root: Path) -> list[str]:
    hooks_root = vendor_root / "hooks"
    generated: list[str] = []

    mapped: dict[str, str] = {}
    unsupported: list[str] = []
    mapped_events: dict[str, str] = {}

    # Primary source: ECC hooks/hooks.json event configuration.
    config_path = hooks_root / "hooks.json"
    if config_path.is_file():
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        events = cfg.get("hooks", {}) if isinstance(cfg, dict) else {}
        for event_name, rules in events.items():
            point = EVENT_TO_POINT.get(event_name)
            if not point:
                unsupported.append(event_name)
                continue

            commands: list[str] = []
            if isinstance(rules, list):
                for rule in rules:
                    for h in (rule or {}).get("hooks", []):
                        if (h or {}).get("type") == "command" and (h or {}).get("command"):
                            commands.append(str(h.get("command")))
            if not commands:
                continue

            ext_dir = output_root / "usr" / "extensions" / point
            ext_dir.mkdir(parents=True, exist_ok=True)
            target = ext_dir / f"_80_ecc_{event_name.lower()}.py"
            command_json = json.dumps(commands)
            content = (
                "from python.helpers.extension import Extension\n"
                "from python.helpers.ecc_sync.hook_runtime import run_hook_commands\n\n"
                "class EccHookBridge(Extension):\n"
                "    async def execute(self, **kwargs):\n"
                f"        commands = {command_json}\n"
                "        payload = {\n"
                f"            'event': '{event_name}',\n"
                "            'kwargs': kwargs,\n"
                "            'agent': str(getattr(self.agent, 'agent_name', '')) if self.agent else '',\n"
                "        }\n"
                f"        plugin_root = {str(vendor_root)!r}\n"
                "        run_hook_commands(commands=commands, payload=payload, plugin_root=__import__('pathlib').Path(plugin_root))\n"
                "        return None\n"
            )
            target.write_text(content, encoding="utf-8")
            rel = str(target.relative_to(output_root)).replace("\\", "/")
            generated.append(rel)
            mapped_events[event_name] = point

    if not hooks_root.is_dir():
        hooks_root = vendor_root / "scripts" / "hooks"
        if not hooks_root.is_dir():
            state_dir = output_root / "usr" / "plugins" / "ecc-integration" / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            report_path = state_dir / "hook_compatibility.json"
            report = {"mapped": mapped, "unsupported": sorted(unsupported), "mapped_events": mapped_events}
            report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            generated.append(str(report_path.relative_to(output_root)).replace("\\", "/"))
            return generated

    for hook_file in sorted(hooks_root.rglob("*")):
        if not hook_file.is_file():
            continue

        point = _resolve_point(hook_file.stem.lower())
        if point is None:
            unsupported.append(hook_file.name)
            continue

        ext_dir = output_root / "usr" / "extensions" / point
        ext_dir.mkdir(parents=True, exist_ok=True)

        target = ext_dir / f"_80_ecc_{hook_file.stem.lower()}.py"
        content = (
            "from python.helpers.extension import Extension\n\n"
            "class EccHookBridge(Extension):\n"
            "    async def execute(self, **kwargs):\n"
            f"        # Source ECC hook: {hook_file.name}\n"
            "        # TODO: execute adapted hook semantics.\n"
            "        return None\n"
        )
        target.write_text(content, encoding="utf-8")
        rel = str(target.relative_to(output_root)).replace("\\", "/")
        generated.append(rel)
        mapped[hook_file.name] = point

    state_dir = output_root / "usr" / "plugins" / "ecc-integration" / "state"
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
