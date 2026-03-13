#!/usr/bin/env python3
"""Initializer for Ea0 plugin payload.

Copies runtime payload into Agent0, wires UI section, ensures EA0 vendor clone,
then runs initial EA0 sync and declares learning scheduler state.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _patch_external_settings(ext_file: Path) -> None:
    text = ext_file.read_text(encoding="utf-8")
    # Migrate prior ECC integration labels/paths to EA0.
    text = text.replace('href="#section-ecc-integration"', 'href="#section-ea0-integration"')
    text = text.replace('id="section-ecc-integration"', 'id="section-ea0-integration"')
    text = text.replace('path="settings/ecc/ecc-settings.html"', 'path="settings/ea0/ea0-settings.html"')
    text = text.replace('alt="ECC Integration"', 'alt="EA0 Integration"')
    text = text.replace('>ECC Integration</span>', '>EA0 Integration</span>')

    nav_insert = """              <li>
                <a href="#section-ea0-integration">
                  <img src="/public/settings.svg" alt="EA0 Integration" />
                  <span>EA0 Integration</span>
                </a>
              </li>
"""
    section_insert = """          <div id="section-ea0-integration" class="section">
            <x-component path="settings/ea0/ea0-settings.html"></x-component>
          </div>
"""

    # Insert nav entry immediately before tunnel entry when missing.
    nav_tunnel = '<a href="#section-tunnel">'
    if "#section-ea0-integration" not in text:
        idx = text.find(nav_tunnel)
        if idx == -1:
            raise RuntimeError(f"Expected tunnel nav anchor not found in {ext_file}")
        li_start = text.rfind("              <li>", 0, idx)
        if li_start == -1:
            raise RuntimeError(f"Could not locate nav insertion point in {ext_file}")
        text = text[:li_start] + nav_insert + text[li_start:]

    # Insert section immediately before tunnel section when missing.
    section_tunnel = '<div id="section-tunnel" class="section">'
    if 'id="section-ea0-integration"' not in text:
        idx = text.find(section_tunnel)
        if idx == -1:
            raise RuntimeError(f"Expected tunnel section anchor not found in {ext_file}")
        text = text[:idx] + section_insert + text[idx:]

    ext_file.write_text(text, encoding="utf-8")


def _ensure_vendor(a0_root: Path) -> Path:
    vendor = a0_root / "usr/everything-claude-code"
    if (vendor / ".git").is_dir():
        return vendor
    if vendor.exists():
        shutil.rmtree(vendor)
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "https://github.com/affaan-m/everything-claude-code.git",
            str(vendor),
        ],
        check=True,
    )
    return vendor


def _run_initial_sync(a0_root: Path, vendor: Path) -> None:
    sys.path.insert(0, str(a0_root))
    from python.helpers.ea0_sync.git_update import get_repo_info
    from python.helpers.ea0_sync.sync import run_sync

    repo = get_repo_info(vendor)
    sha = repo.get("current_sha") or "local"
    result = run_sync(vendor_root=vendor, workspace_root=a0_root, source_sha=sha)
    if not result.success:
        raise RuntimeError("EA0 initial sync failed")


def _ensure_learning_scheduler(a0_root: Path) -> None:
    sys.path.insert(0, str(a0_root))
    from python.helpers.ea0_sync.learning_scheduler import ensure_learning_schedule

    asyncio.run(ensure_learning_schedule(workspace_root=a0_root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a0-root", required=True)
    parser.add_argument("--plugin-root", required=True)
    args = parser.parse_args()

    a0_root = Path(args.a0_root).resolve()
    plugin_root = Path(args.plugin_root).resolve()
    runtime = plugin_root / "runtime"

    if not (a0_root / "python").is_dir() or not (a0_root / "webui").is_dir():
        raise RuntimeError(f"Target does not look like Agent0 root: {a0_root}")
    if not runtime.is_dir():
        raise RuntimeError(f"Missing runtime directory: {runtime}")

    print("[init 1/6] Installing EA0 backend modules...")
    _copy(runtime / "python/api/ea0_sync.py", a0_root / "python/api/ea0_sync.py")
    _copy(runtime / "python/tools/ea0_sync_tool.py", a0_root / "python/tools/ea0_sync_tool.py")
    _copy(runtime / "python/tools/ea0_learning_tool.py", a0_root / "python/tools/ea0_learning_tool.py")
    helpers_src = runtime / "python/helpers/ea0_sync"
    helpers_dst = a0_root / "python/helpers/ea0_sync"
    helpers_dst.mkdir(parents=True, exist_ok=True)
    for file in helpers_src.glob("*.py"):
        _copy(file, helpers_dst / file.name)

    print("[init 2/6] Installing EA0 settings UI components...")
    _copy(
        runtime / "webui/components/settings/ea0/ea0-settings.html",
        a0_root / "webui/components/settings/ea0/ea0-settings.html",
    )
    _copy(
        runtime / "webui/components/settings/ea0/ea0-store.js",
        a0_root / "webui/components/settings/ea0/ea0-store.js",
    )

    print("[init 3/6] Wiring EA0 section under External Services...")
    _patch_external_settings(a0_root / "webui/components/settings/external/external-settings.html")

    print("[init 4/6] Installing EA0 prompt injection + core memory...")
    _copy(
        runtime / "usr/extensions/system_prompt/_50_ea0_context.py",
        a0_root / "usr/extensions/system_prompt/_50_ea0_context.py",
    )
    _copy(
        runtime / "usr/prompts/fw.ea0.reference.md",
        a0_root / "usr/prompts/fw.ea0.reference.md",
    )
    _copy(
        runtime / "usr/knowledge/core-memories/ea0/agent0-ea0-integration.md",
        a0_root / "usr/knowledge/core-memories/ea0/agent0-ea0-integration.md",
    )

    print("[init 5/6] Ensuring EA0 vendor checkout exists...")
    vendor = _ensure_vendor(a0_root)

    print("[init 6/6] Running EA0 initial sync...")
    _run_initial_sync(a0_root, vendor)
    _ensure_learning_scheduler(a0_root)

    print("Ea0 initialization completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
