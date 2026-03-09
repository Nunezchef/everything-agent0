from __future__ import annotations

from pathlib import Path
import shutil


def transform_core_memories(vendor_root: Path, output_root: Path) -> list[str]:
    src_base = vendor_root / "contexts"
    dst_base = output_root / "usr" / "knowledge" / "core-memories" / "ecc"
    generated: list[str] = []

    if not src_base.is_dir():
        return generated

    for src_file in sorted(src_base.rglob("*")):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(src_base)
        dst_file = dst_base / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        generated.append(str(dst_file.relative_to(output_root)).replace("\\", "/"))

    # Integration memory ensures Agent0 is explicitly aware ECC is active and available.
    integration_memory = dst_base / "agent0-ecc-integration.md"
    integration_memory.parent.mkdir(parents=True, exist_ok=True)
    integration_memory.write_text(
        (
            "# ECC Integration Active\n\n"
            "ECC integration is installed and active in this Agent0 workspace.\n\n"
            "## Operating Guidance\n"
            "- Prefer ECC-provided capabilities when they help complete the user's request faster or with better quality.\n"
            "- Use ECC skills under `usr/skills/ecc/` when a matching workflow exists.\n"
            "- Use ECC specialist agents under `usr/agents/ecc/` for targeted review, planning, testing, and refactoring tasks.\n"
            "- Use ECC command knowledge under `usr/knowledge/ecc-commands/` for command-oriented workflows.\n"
            "- Keep ECC hooks and toolchain compatibility intact; do not remove generated ECC extensions unless explicitly asked.\n\n"
            "## Safety and Scope\n"
            "- Follow user instructions and repository constraints first.\n"
            "- If ECC behavior conflicts with explicit user direction, follow the user and explain the tradeoff briefly.\n"
        ),
        encoding="utf-8",
    )
    generated.append(str(integration_memory.relative_to(output_root)).replace("\\", "/"))

    reference_prompt = output_root / "usr" / "prompts" / "fw.ecc.reference.md"
    reference_prompt.parent.mkdir(parents=True, exist_ok=True)
    reference_prompt.write_text(
        (
            "# ECC Workflow Integration\n\n"
            "ECC integration is active for this Agent0 instance.\n\n"
            "Use ECC assets proactively when they improve execution quality or speed:\n"
            "- Skills: `usr/skills/ecc/`\n"
            "- Specialist agents: `usr/agents/ecc/`\n"
            "- Command knowledge: `usr/knowledge/ecc-commands/`\n"
            "- Hook/toolchain outputs: `usr/extensions/*_ecc_*` and `usr/plugins/ecc-integration/tools/`\n\n"
            "When planning or implementing work:\n"
            "- Prefer ECC workflows for TDD, review, verification, orchestration, and refactoring when relevant.\n"
            "- Keep ECC-generated integration assets intact unless the user explicitly requests removal.\n"
            "- Follow explicit user instructions first when they conflict with ECC defaults.\n"
        ),
        encoding="utf-8",
    )
    generated.append(str(reference_prompt.relative_to(output_root)).replace("\\", "/"))

    context_extension = output_root / "usr" / "extensions" / "system_prompt" / "_50_ecc_context.py"
    context_extension.parent.mkdir(parents=True, exist_ok=True)
    context_extension.write_text(
        (
            "from python.helpers.extension import Extension\n"
            "from python.helpers import files\n\n\n"
            "class EccContext(Extension):\n"
            "    async def execute(self, system_prompt: list[str] = [], **kwargs):\n"
            "        prompt = ''\n"
            "        if self.agent:\n"
            "            try:\n"
            "                prompt = self.agent.read_prompt('fw.ecc.reference.md')\n"
            "            except Exception:\n"
            "                prompt = ''\n"
            "        if not prompt:\n"
            "            memory_path = files.get_abs_path(\n"
            "                'usr',\n"
            "                'knowledge',\n"
            "                'core-memories',\n"
            "                'ecc',\n"
            "                'agent0-ecc-integration.md',\n"
            "            )\n"
            "            if files.exists(memory_path):\n"
            "                prompt = files.read_file(memory_path)\n"
            "        if prompt:\n"
            "            system_prompt.append(prompt)\n"
        ),
        encoding="utf-8",
    )
    generated.append(str(context_extension.relative_to(output_root)).replace("\\", "/"))

    return generated
