# Everything Agent0 (Ea0 / ECC Plugin)

Everything Agent0 is a standalone Agent0 plugin repository that integrates **Everything Claude Code (ECC)** into a clean Agent0 install.

It provides:
- ECC asset sync into Agent0 (`skills`, `agents`, `commands`, `core memories`, `ecosystem tools`)
- ECC hook mapping from Claude-style events into Agent0 extension points
- ECC settings panel under **Settings -> External Services -> ECC Integration**
- One-click actions: **Install/Sync**, **Update Latest (Git)**, **Create Backup Point**, **Restore Backup**
- Git visibility in UI: repo URL, current vendor SHA, installed/synced SHA, last sync
- Prompt injection so Agent0 knows ECC is active and should use ECC workflow assets

## What Ea0 Changes in Agent0

### Backend
Installs:
- `python/api/ecc_sync.py`
- `python/tools/ecc_sync_tool.py`
- `python/helpers/ecc_sync/*.py`

Provides ECC API actions:
- `status`
- `sync`
- `update_latest`
- `backup_create`
- `backup_list`
- `backup_restore`

### UI
Installs:
- `webui/components/settings/ecc/ecc-settings.html`
- `webui/components/settings/ecc/ecc-store.js`

Patches:
- `webui/components/settings/external/external-settings.html`

### Prompt & Memory Integration
Installs:
- `usr/extensions/system_prompt/_50_ecc_context.py`
- `usr/prompts/fw.ecc.reference.md`
- `usr/knowledge/core-memories/ecc/agent0-ecc-integration.md`

This follows the same pattern used by superpowers-style integrations: a system_prompt extension appends an ECC reference prompt each run.

## Install into a Fresh Agent0

### 1) Clone this plugin repo
```bash
git clone https://github.com/Nunezchef/everything-agent0.git
cd everything-agent0
```

### 2) Run installer against your Agent0 root
```bash
./scripts/install-into-agent0.sh /a0
```

If your Agent0 path is different, replace `/a0`.

### 3) Restart Agent0
Restart is required so new extensions are loaded.

## Post-Install Verification

1. Open Agent0 settings:
- `Settings -> External Services -> ECC Integration`

2. Confirm visible fields:
- Health status
- ECC Git repository
- Current version
- Installed version
- Last sync
- Injection status flags

3. Confirm runtime files exist:
- `usr/extensions/system_prompt/_50_ecc_context.py`
- `usr/prompts/fw.ecc.reference.md`
- `usr/knowledge/core-memories/ecc/agent0-ecc-integration.md`

4. Use `Install / Sync ECC` once in UI.

## Update Flow

From ECC settings UI:
- `Update Latest (Git)` pulls latest ECC vendor and re-syncs generated assets.
- Optionally enable `Backup Before Update`.
- Use `Restore Backup` if rollback is needed.

## Backup & State

ECC integration state lives under:
- `usr/plugins/ecc-integration/state/manifest.json`
- `usr/plugins/ecc-integration/state/vendor_state.json`
- `usr/plugins/ecc-integration/state/hook_compatibility.json`
- `usr/plugins/ecc-integration/backups/`

## Important Notes

- This repo is **plugin-only** (not a fork of Agent0).
- Installer patches one Agent0 UI file (`external-settings.html`) to add ECC section link.
- If you reinstall Agent0, re-run installer to restore ECC integration.

## Development

If you modify runtime files in this repo, rerun:
```bash
./scripts/install-into-agent0.sh /a0
```

Then restart Agent0.
