from __future__ import annotations

import ast
import json
import re
from pathlib import Path


TOOL_CAPABILITY_MAP = {
    "Read": "filesystem-read-write",
    "Write": "filesystem-read-write",
    "Edit": "filesystem-read-write",
    "Grep": "search",
    "Glob": "search",
    "Bash": "shell-execution",
}


def _normalize_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower().replace("_", "-").replace(" ", "-"))
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "unnamed-agent"


def _titleize_name(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_\s]+", value) if part)


def _parse_frontmatter(text: str) -> tuple[dict[str, object], str, list[str]]:
    warnings: list[str] = []
    if not text.startswith("---\n"):
        warnings.append("missing_frontmatter")
        return {}, text, warnings

    end = text.find("\n---\n", 4)
    if end == -1:
        warnings.append("malformed_frontmatter")
        return {}, text, warnings

    raw_meta = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, object] = {}

    for line in raw_meta.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value.startswith("[") and value.endswith("]"):
            try:
                meta[key] = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                warnings.append(f"invalid_list:{key}")
                meta[key] = []
        else:
            meta[key] = value.strip("\"'")

    return meta, body, warnings


def _extract_title(body: str, fallback_name: str, warnings: list[str]) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    warnings.append("missing_h1")
    return _titleize_name(fallback_name)


def _normalize_body(body: str) -> str:
    normalized = body.strip()
    return normalized if normalized else "No instructions provided."


def _format_tools(tools: list[str]) -> str:
    if not tools:
        return "none"
    return ", ".join(f"`{tool}`" for tool in tools)


def _format_capabilities(capabilities: list[str]) -> str:
    if not capabilities:
        return "none"
    return ", ".join(f"`{capability}`" for capability in capabilities)


def _map_capabilities(tools: list[str], warnings: list[str]) -> list[str]:
    mapped: list[str] = []
    for tool in tools:
        capability = TOOL_CAPABILITY_MAP.get(tool)
        if capability:
            mapped.append(capability)
        else:
            warnings.append(f"unknown_tool:{tool}")
    return sorted(set(mapped))


def _build_context(
    *,
    title: str,
    description: str,
    ecc_name: str,
    model: str,
    tools: list[str],
    capabilities: list[str],
    instructions: str,
) -> str:
    role = description or f"Generated EA0 agent derived from ECC agent `{ecc_name}`."
    lines = [
        f"# {title}",
        "",
        "## Role",
        role,
        "",
        "## Agent0 Compatibility",
        f"- Source agent: `{ecc_name}`",
        f"- Original ECC model: `{model or 'none'}`",
        f"- Original ECC tools: {_format_tools(tools)}",
        f"- Agent0 capability mapping: {_format_capabilities(capabilities)}",
        "",
        "## Instructions",
        instructions,
        "",
    ]
    return "\n".join(lines)


def transform_agents(vendor_root: Path, output_root: Path) -> list[str]:
    src_base = vendor_root / "agents"
    dst_base = output_root / "usr" / "agents"
    generated: list[str] = []
    registry_entries: list[dict[str, object]] = []

    if not src_base.is_dir():
        return generated

    for src_file in sorted(src_base.glob("*.md")):
        raw_text = src_file.read_text(encoding="utf-8")
        meta, body, warnings = _parse_frontmatter(raw_text)

        ecc_name = str(meta.get("name") or src_file.stem).strip() or src_file.stem
        normalized_name = f"ea0-{_normalize_name(ecc_name)}"
        title = _extract_title(body, ecc_name, warnings)
        description = str(meta.get("description") or "").strip()
        tools = [str(tool) for tool in meta.get("tools", [])] if isinstance(meta.get("tools"), list) else []
        model = str(meta.get("model") or "").strip()
        capabilities = _map_capabilities(tools, warnings)
        instructions = _normalize_body(body)

        agent_dir = dst_base / normalized_name
        agent_dir.mkdir(parents=True, exist_ok=True)

        agent_json = {
            "title": f"EA0 {title}",
            "description": description,
            "context": "",
            "enabled": True,
        }
        agent_json_path = agent_dir / "agent.json"
        agent_json_path.write_text(json.dumps(agent_json, indent=2) + "\n", encoding="utf-8")
        generated.append(str(agent_json_path.relative_to(output_root)).replace("\\", "/"))

        context_path = agent_dir / "_context.md"
        context_path.write_text(
            _build_context(
                title=title,
                description=description,
                ecc_name=ecc_name,
                model=model,
                tools=tools,
                capabilities=capabilities,
                instructions=instructions,
            ),
            encoding="utf-8",
        )
        generated.append(str(context_path.relative_to(output_root)).replace("\\", "/"))

        registry_entries.append(
            {
                "source": str(src_file.relative_to(vendor_root)).replace("\\", "/"),
                "ecc_name": ecc_name,
                "generated_name": normalized_name,
                "title": agent_json["title"],
                "description": description,
                "ecc_model": model,
                "ecc_tools": tools,
                "mapped_capabilities": capabilities,
                "warnings": warnings,
            }
        )

    state_dir = output_root / "usr" / "plugins" / "ea0-integration" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    registry_path = state_dir / "agents.json"
    registry_path.write_text(
        json.dumps({"agents": registry_entries}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    generated.append(str(registry_path.relative_to(output_root)).replace("\\", "/"))

    return generated
