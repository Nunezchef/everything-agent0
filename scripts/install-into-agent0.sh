#!/usr/bin/env bash
set -euo pipefail

A0_ROOT="${1:-/a0}"
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_ROOT="$PLUGIN_ROOT/runtime"

if [[ ! -d "$A0_ROOT/python" || ! -d "$A0_ROOT/webui" ]]; then
  echo "error: target does not look like Agent0 root: $A0_ROOT" >&2
  exit 1
fi

echo "[1/7] Installing ECC backend modules..."
mkdir -p "$A0_ROOT/python/helpers/ecc_sync"
cp -f "$RUNTIME_ROOT/python/api/ecc_sync.py" "$A0_ROOT/python/api/ecc_sync.py"
cp -f "$RUNTIME_ROOT/python/tools/ecc_sync_tool.py" "$A0_ROOT/python/tools/ecc_sync_tool.py"
cp -f "$RUNTIME_ROOT/python/helpers/ecc_sync/"*.py "$A0_ROOT/python/helpers/ecc_sync/"

echo "[2/7] Installing ECC settings UI components..."
mkdir -p "$A0_ROOT/webui/components/settings/ecc"
cp -f "$RUNTIME_ROOT/webui/components/settings/ecc/ecc-settings.html" "$A0_ROOT/webui/components/settings/ecc/ecc-settings.html"
cp -f "$RUNTIME_ROOT/webui/components/settings/ecc/ecc-store.js" "$A0_ROOT/webui/components/settings/ecc/ecc-store.js"

echo "[3/7] Wiring ECC section under External Services..."
EXT_FILE="$A0_ROOT/webui/components/settings/external/external-settings.html"
if ! grep -q "section-ecc-integration" "$EXT_FILE"; then
  awk '
    BEGIN{added_nav=0; added_section=0}
    /<li>[[:space:]]*$/ && !added_nav {print}
    /<a href="#section-tunnel">/ && !added_nav {
      print "              <li>"
      print "                <a href=\"#section-ecc-integration\">"
      print "                  <img src=\"/public/settings.svg\" alt=\"ECC Integration\" />"
      print "                  <span>ECC Integration</span>"
      print "                </a>"
      print "              </li>"
      added_nav=1
    }
    {print}
    /<div id="section-update-checker" class="section">/ && !added_section {
      getline; print
      getline; print
      print "          <div id=\"section-ecc-integration\" class=\"section\">"
      print "            <x-component path=\"settings/ecc/ecc-settings.html\"></x-component>"
      print "          </div>"
      added_section=1
    }
  ' "$EXT_FILE" > "$EXT_FILE.tmp"
  mv "$EXT_FILE.tmp" "$EXT_FILE"
fi

echo "[4/7] Installing ECC prompt injection + core memory..."
mkdir -p "$A0_ROOT/usr/extensions/system_prompt" "$A0_ROOT/usr/prompts" "$A0_ROOT/usr/knowledge/core-memories/ecc"
cp -f "$RUNTIME_ROOT/usr/extensions/system_prompt/_50_ecc_context.py" "$A0_ROOT/usr/extensions/system_prompt/_50_ecc_context.py"
cp -f "$RUNTIME_ROOT/usr/prompts/fw.ecc.reference.md" "$A0_ROOT/usr/prompts/fw.ecc.reference.md"
cp -f "$RUNTIME_ROOT/usr/knowledge/core-memories/ecc/agent0-ecc-integration.md" "$A0_ROOT/usr/knowledge/core-memories/ecc/agent0-ecc-integration.md"

echo "[5/7] Ensuring ECC vendor checkout exists..."
if [[ ! -d "$A0_ROOT/usr/everything-claude-code/.git" ]]; then
  rm -rf "$A0_ROOT/usr/everything-claude-code"
  git clone --depth 1 https://github.com/affaan-m/everything-claude-code.git "$A0_ROOT/usr/everything-claude-code"
fi

echo "[6/7] Running ECC initial sync..."
PYTHONPATH="$A0_ROOT" python3 - <<PY
from pathlib import Path
from python.helpers.ecc_sync.git_update import get_repo_info
from python.helpers.ecc_sync.sync import run_sync
vendor = Path("$A0_ROOT/usr/everything-claude-code")
repo = get_repo_info(vendor)
sha = repo.get("current_sha") or "local"
res = run_sync(vendor_root=vendor, workspace_root=Path("$A0_ROOT"), source_sha=sha)
print("sync_success", res.success)
print("generated_count", len(res.generated_paths))
print("health", res.health_report.get("status"))
PY

echo "[7/7] Done. Restart Agent0 to load newly installed extensions."
