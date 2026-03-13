# Design: ECC Agent Transformer

## Overview

ECC agents are defined as markdown files with YAML frontmatter. Agent0 expects an agent directory with structured files. This change introduces a transformer that projects ECC agent definitions into Agent0-native agent directories while preserving enough ECC metadata for traceability and later compatibility work.

## Source Format

Expected ECC agent shape:

```md
---
name: code-reviewer
description: Expert code review specialist...
tools: ["Read", "Grep", "Glob", "Bash"]
model: sonnet
---

# Code Reviewer

You are a senior code reviewer...
```

Supported source fields:

- `name`
- `description`
- `tools`
- `model`
- first H1 in markdown body
- remaining markdown body

## Target Format

Generated Agent0 output:

```text
usr/agents/ea0-<normalized-name>/
├── agent.json
└── _context.md
```

### `agent.json`

Generated shape:

```json
{
  "title": "EA0 Code Reviewer",
  "description": "Expert code review specialist...",
  "context": "",
  "enabled": true
}
```

Field mapping:

- `title`: `EA0 ` + first H1, else titleized ECC `name`
- `description`: ECC `description`
- `context`: empty string
- `enabled`: `true`

### `_context.md`

Generated shape:

```md
# Code Reviewer

## Role
Expert code review specialist...

## Agent0 Compatibility
- Source agent: `code-reviewer`
- Original ECC model: `sonnet`
- Original ECC tools: `Read`, `Grep`, `Glob`, `Bash`
- Agent0 capability mapping: `filesystem-read-write`, `shell-execution`, `search`

## Instructions
<normalized ECC body>
```

The transformer should preserve markdown structure and operational instructions while applying only minimal, deterministic compatibility rewrites.

## Capability Mapping

ECC `tools` should be transformed into Agent0 capability metadata.

Initial mapping:

| ECC tool | Agent0 capability |
|---|---|
| `Read` | `filesystem-read-write` |
| `Write` | `filesystem-read-write` |
| `Edit` | `filesystem-read-write` |
| `Grep` | `search` |
| `Glob` | `search` |
| `Bash` | `shell-execution` |

Unmapped tools:

- are preserved in metadata
- produce transformation warnings
- do not block generation

## Model Handling

ECC `model` values should be preserved as advisory metadata only.

This change does not enforce per-agent model routing in Agent0.

## Naming

Generated directory naming:

```text
ea0-<normalized-ecc-name>
```

Normalization rules:

- lowercase
- replace spaces and underscores with `-`
- remove unsupported characters
- collapse repeated dashes

The `ea0-` prefix prevents collisions with native or user-defined Agent0 agents.

## Metadata Registry

The transformer should emit agent metadata into plugin state:

```text
usr/plugins/ea0-integration/state/agents.json
```

Registry entry shape:

```json
{
  "source": "agents/code-reviewer.md",
  "ecc_name": "code-reviewer",
  "generated_name": "ea0-code-reviewer",
  "title": "EA0 Code Reviewer",
  "description": "Expert code review specialist...",
  "ecc_model": "sonnet",
  "ecc_tools": ["Read", "Grep", "Glob", "Bash"],
  "mapped_capabilities": [
    "filesystem-read-write",
    "search",
    "shell-execution"
  ],
  "warnings": []
}
```

## Fallback Behavior

If frontmatter is missing or malformed:

- derive `name` from filename
- derive title from first H1 or titleized filename
- leave description empty
- preserve body when available
- add a warning entry

## Sync Integration

The existing sync pipeline should:

1. transform ECC markdown agents into staged Agent0 agent directories
2. add generated agent files to the manifest
3. add the shared agent registry to the manifest
4. delete stale generated agent outputs during sync

## Verification

This change is complete when:

- generated agents exist under `usr/agents/ea0-*`
- Agent0 discovers them as selectable agent profiles
- generated agents include valid `agent.json`
- metadata registry records tool/model details and warnings

## Future Work

- stronger prompt normalization for Claude-specific language
- optional model hints or routing
- optional capability enforcement if Agent0 later supports it
