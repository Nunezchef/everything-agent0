# Tasks

## 1. Transformer

- [ ] Update the agent transformer to parse ECC markdown agents instead of copying raw files
- [ ] Generate `usr/agents/ea0-<name>/agent.json`
- [ ] Generate `usr/agents/ea0-<name>/_context.md`
- [ ] Normalize ECC agent names for Agent0 directory use

## 2. Metadata

- [ ] Add ECC tool-to-Agent0 capability mapping
- [ ] Preserve original ECC `tools` and `model` values in plugin state
- [ ] Emit `usr/plugins/ea0-integration/state/agents.json`
- [ ] Record transform warnings for malformed or partially supported agent inputs

## 3. Sync Integration

- [ ] Include generated agent outputs and registry files in the sync manifest
- [ ] Ensure stale generated agent files are removed correctly on later syncs

## 4. Verification

- [ ] Verify at least one generated EA0 agent appears in Agent0's profile dropdown
- [ ] Verify generated `agent.json` files are readable by Agent0 subagent loading
- [ ] Verify transformed agent instructions preserve core ECC behavior
