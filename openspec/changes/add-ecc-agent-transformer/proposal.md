# Proposal: Add ECC Agent Transformer

## Summary

Add a dedicated transformer that converts ECC agents from `agents/*.md` into valid Agent0 agents under `usr/agents/*`, so they can be discovered by Agent0 and selected from the default agent profile dropdown in Settings.

## Problem

Ea0 currently copies ECC agent source files, but Agent0 does not consume raw ECC markdown agents directly. Agent0 expects each agent to exist as a directory containing at least an `agent.json` file and optionally `_context.md` and prompt files.

Without a real transformation layer:

- ECC agents are not guaranteed to be usable as Agent0 agents
- ECC agents are not guaranteed to appear in the Agent0 profile dropdown
- ECC `tools` and `model` metadata are lost or treated opaquely
- Ea0 cannot truthfully claim native agent compatibility

## Goals

- Transform ECC agents into valid Agent0 agent directories
- Preserve ECC agent intent, title, description, and instruction body
- Map ECC `tools` into Agent0 capability metadata where possible
- Preserve unsupported ECC tool or model details as metadata
- Ensure generated agents are discoverable by Agent0 without custom UI work
- Track generated agent metadata for debugging and sync reporting

## Non-Goals

- Enforcing ECC tool allowlists at runtime
- Enforcing ECC model selection at runtime
- Full natural-language rewriting of every ECC agent prompt
- Translating non-agent assets in this change

## Proposed Change

Implement a new agent transformation flow that:

1. Reads ECC agents from `agents/*.md`
2. Parses YAML frontmatter and markdown body
3. Generates Agent0-compatible output under `usr/agents/ea0-<name>/`
4. Emits:
   - `agent.json`
   - `_context.md`
5. Records transformation metadata in Ea0 plugin state

## User Impact

After sync:

- ECC agents appear as Agent0 profiles
- users can select generated EA0 agents from Agent Settings
- generated agents preserve their operational purpose and instructions
- Ea0 has a stable foundation for later improvements such as tool compatibility hints and model routing

## Risks

- ECC prompts may contain Claude-specific assumptions that still need later normalization
- some ECC tool metadata may not have direct Agent0 equivalents
- name collisions must be handled deterministically

## Success Criteria

- At least one transformed ECC agent appears in Agent0's profile dropdown
- Generated agents are valid Agent0 agent directories
- ECC `tools` and `model` are preserved in transformer metadata
- Sync reports generated agent outputs and warnings
