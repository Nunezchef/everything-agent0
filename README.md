# Everything Agent0 (Ea0)

Ea0 is a **plugin-only integration layer** that ports Everything Claude Code (ECC) into Agent0.

It does not ship a fork of Agent0.  
It installs a runtime transformer pipeline that:
- pulls ECC content from `usr/everything-claude-code`
- transforms it into Agent0-compatible layout
- injects ECC workflow guidance into Agent0 system prompt
- maps ECC hooks/events into Agent0 extension points
- provides UI controls for sync, update, backup, restore

## Scope

Ea0 integrates the ECC ecosystem into Agent0 in six domains:
- Skills
- Agents
- Command knowledge
- Hook bridges
- Ecosystem tools/scripts
- Core memory + system prompt context

## Architecture

Ea0 runtime consists of:
- API: `python/api/ecc_sync.py`
- Tool: `python/tools/ecc_sync_tool.py`
- Transformers: `python/helpers/ecc_sync/*.py`
- UI panel: `webui/components/settings/ecc/*`
- Prompt injection: `usr/extensions/system_prompt/_50_ecc_context.py`

### Transformation model

Ea0 does not use ECC files in-place inside Agent0 runtime. It transforms and writes generated outputs into `usr/*` and state under `usr/plugins/ecc-integration/state/*`.

Primary flow:
1. Resolve ECC vendor root (`usr/everything-claude-code`)
2. Transform ECC domains into Agent0 targets
3. Write manifest/vendor state
4. Remove stale previously-generated files
5. Promote staged outputs into workspace
6. Recompute health report

## ECC -> Agent0 Mapping

| ECC domain | Agent0 output |
|---|---|
| skills | `usr/skills/ecc/*` |
| agents | `usr/agents/ecc/*` |
| command docs | `usr/knowledge/ecc-commands/*` |
| contexts | `usr/knowledge/core-memories/ecc/*` |
| scripts/tools | `usr/plugins/ecc-integration/tools/*` |
| hook config/events | `usr/extensions/*/_80_ecc_*.py` |

## Hook Integration

ECC event semantics are bridged into Agent0 extension points:

| ECC event | Agent0 extension point |
|---|---|
| `SessionStart` | `agent_init` |
| `PreToolUse` | `tool_execute_before` |
| `PostToolUse` | `tool_execute_after` |
| `PreCompact` | `message_loop_prompts_before` |
| `SessionEnd` | `message_loop_end` |
| `Stop` | `message_loop_end` |

Hook command execution is handled by:
- `python/helpers/ecc_sync/hook_runtime.py`

Safety guarantees:
- non-JSON payload objects are normalized before serialization
- command timeout guard is enforced
- failures are isolated to hook result payload (non-fatal to core flow)

## System Prompt / Memory Integration

Ea0 follows the same pattern used by framework-style prompt integrations:

1. `usr/extensions/system_prompt/_50_ecc_context.py` appends ECC context each run
2. primary source: `usr/prompts/fw.ecc.reference.md`
3. fallback source: `usr/knowledge/core-memories/ecc/agent0-ecc-integration.md`

This ensures Agent0 explicitly knows ECC is active and can prioritize ECC capabilities during execution.

## Settings UI Integration

Ea0 adds:
- `Settings -> External Services -> ECC Integration`

Panel capabilities:
- `Install / Sync ECC`
- `Update Latest (Git)`
- `Create Backup Point`
- `Restore Backup`

Panel status fields:
- health status
- ECC git repository URL
- current vendor SHA
- installed/synced SHA
- last sync timestamp
- injection status flags (extension/prompt/core-memory)

## API Actions

Endpoint: `/ecc_sync`

Supported actions:
- `status`
- `sync`
- `update_latest`
- `backup_create`
- `backup_list`
- `backup_restore`

## Quick Install (Copy/Paste)

Use this exact flow on a fresh Agent0 instance:

```bash
cd /a0/usr/workdir
rm -rf .a0-install
git clone --branch main https://github.com/Nunezchef/Ea0.git .a0-install
bash /a0/usr/workdir/.a0-install/install.sh /a0
```

Then restart Agent0.

If your Agent0 root is not `/a0`, replace the final argument with your real Agent0 root path.

## One-Line Agent0 Prompt

If you want Agent0 to run installation for you, paste this:

```text
Install this plugin from main branch only: https://github.com/Nunezchef/Ea0.git. Clone it into /a0/usr/workdir/.a0-install and run: bash /a0/usr/workdir/.a0-install/install.sh /a0
```

## Post-Install Check

After restart, verify:
1. Open `Settings -> External Services -> ECC Integration`
2. Click `Install / Sync ECC`
3. Confirm status fields populate (health, repo URL, vendor SHA, synced SHA, last sync)
4. Confirm health is `healthy`

## Troubleshooting (Common Install Errors)

| Symptom | Cause | Fix |
|---|---|---|
| `No such file or directory: /a0/.a0-install/...` | Wrong clone path | Use `/a0/usr/workdir/.a0-install/...` |
| `Error: Branch parameter is empty` | Wrong script used (`install_A0.sh`) | Use plugin installer `install.sh` |
| `ECC tab missing in UI` | Installer not run against live Agent0 root | Re-run installer with correct root, then restart Agent0 |
| Sync fails on vendor path | ECC vendor root missing | Open ECC panel and run `Install / Sync ECC` after install |

## Operational Workflows

### First-time bootstrap
1. run installer
2. restart Agent0
3. open ECC Integration panel
4. run `Install / Sync ECC`
5. verify health = `healthy`

### Daily workflow
1. use Agent0 normally with ECC-enabled prompts/hooks
2. update when needed with `Update Latest (Git)`
3. keep `Backup Before Update` enabled for safe rollback

### Safe upgrade workflow
1. create backup point
2. update latest
3. verify injection flags and hook health
4. rollback using `Restore Backup` if required

### Disaster recovery workflow
1. reinstall Agent0 base
2. reinstall Ea0 plugin
3. re-run sync
4. restore backup point from `usr/plugins/ecc-integration/backups/` if needed

## Verification Checklist

After install/sync:
- ECC panel appears under External Services
- `status.health_report.status == healthy`
- injection flags all active
- generated ECC files present in `usr/skills/ecc`, `usr/agents/ecc`, `usr/knowledge/ecc-commands`
- hook bridges present under `usr/extensions/*_ecc_*.py`
- manifest exists at `usr/plugins/ecc-integration/state/manifest.json`

CLI checks:
```bash
test -f /a0/usr/plugins/ecc-integration/state/manifest.json
test -f /a0/usr/extensions/system_prompt/_50_ecc_context.py
test -f /a0/usr/prompts/fw.ecc.reference.md
test -d /a0/usr/skills/ecc
test -d /a0/usr/agents/ecc
```

## Repository Layout

- `plugin.yaml`: plugin metadata
- `hooks.md`: runtime hook behavior summary
- `install.sh`: primary community-style installer
- `initialize.py`: plugin initializer (applies runtime payload + initial ECC sync)
- `scripts/install-into-agent0.sh`: compatibility wrapper to `install.sh`
- `runtime/python/*`: API/tool/transform runtime payload
- `runtime/webui/*`: ECC settings UI payload
- `runtime/usr/*`: prompt/memory/system_prompt payload

## Notes

- Repo is intentionally plugin-only.
- Installer patches `webui/components/settings/external/external-settings.html` once (idempotent guard included).
- Re-run installer after Agent0 upgrades/reinstalls.
