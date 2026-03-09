#!/usr/bin/env python3
"""Initializer for Ea0 plugin payload.

Copies runtime payload into Agent0, wires UI section, ensures ECC vendor clone,
then runs initial ECC sync.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _patch_external_settings(ext_file: Path) -> None:
    text = ext_file.read_text(encoding="utf-8")
    if "section-ecc-integration" in text:
        return

    nav_anchor = """              <li>
                <a href="#section-tunnel">
"""
    nav_insert = """              <li>
                <a href="#section-ecc-integration">
                  <img src="/public/settings.svg" alt="ECC Integration" />
                  <span>ECC Integration</span>
                </a>
              </li>
"""
    section_anchor = """          <div id="section-update-checker" class="section">
            <x-component path="settings/update-checker/update-checker.html"></x-component>
          </div>
"""
    section_insert = """          <div id="section-ecc-integration" class="section">
            <x-component path="settings/ecc/ecc-settings.html"></x-component>
          </div>
"""

    if nav_anchor not in text:
        raise RuntimeError(f"Expected navigation anchor not found in {ext_file}")
    if section_anchor not in text:
        raise RuntimeError(f"Expected section anchor not found in {ext_file}")

    text = text.replace(nav_anchor, nav_insert + nav_anchor, 1)
    text = text.replace(section_anchor, section_anchor + section_insert, 1)
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
    from python.helpers.ecc_sync.git_update import get_repo_info
    from python.helpers.ecc_sync.sync import run_sync

    repo = get_repo_info(vendor)
    sha = repo.get("current_sha") or "local"
    result = run_sync(vendor_root=vendor, workspace_root=a0_root, source_sha=sha)
    if not result.success:
        raise RuntimeError("ECC initial sync failed")


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

    print("[init 1/6] Installing ECC backend modules...")
    _copy(runtime / "python/api/ecc_sync.py", a0_root / "python/api/ecc_sync.py")
    _copy(runtime / "python/tools/ecc_sync_tool.py", a0_root / "python/tools/ecc_sync_tool.py")
    helpers_src = runtime / "python/helpers/ecc_sync"
    helpers_dst = a0_root / "python/helpers/ecc_sync"
    helpers_dst.mkdir(parents=True, exist_ok=True)
    for file in helpers_src.glob("*.py"):
        _copy(file, helpers_dst / file.name)

    print("[init 2/6] Installing ECC settings UI components...")
    _copy(
        runtime / "webui/components/settings/ecc/ecc-settings.html",
        a0_root / "webui/components/settings/ecc/ecc-settings.html",
    )
    _copy(
        runtime / "webui/components/settings/ecc/ecc-store.js",
        a0_root / "webui/components/settings/ecc/ecc-store.js",
    )

    print("[init 3/6] Wiring ECC section under External Services...")
    _patch_external_settings(a0_root / "webui/components/settings/external/external-settings.html")

    print("[init 4/6] Installing ECC prompt injection + core memory...")
    _copy(
        runtime / "usr/extensions/system_prompt/_50_ecc_context.py",
        a0_root / "usr/extensions/system_prompt/_50_ecc_context.py",
    )
    _copy(
        runtime / "usr/prompts/fw.ecc.reference.md",
        a0_root / "usr/prompts/fw.ecc.reference.md",
    )
    _copy(
        runtime / "usr/knowledge/core-memories/ecc/agent0-ecc-integration.md",
        a0_root / "usr/knowledge/core-memories/ecc/agent0-ecc-integration.md",
    )

    print("[init 5/6] Ensuring ECC vendor checkout exists...")
    vendor = _ensure_vendor(a0_root)

    print("[init 6/6] Running ECC initial sync...")
    _run_initial_sync(a0_root, vendor)

    print("Ea0 initialization completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
