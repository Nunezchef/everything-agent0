# Design: EA0 Continuous Learning v1

## Overview

EA0 continuous-learning v1 should be implemented as a plugin-owned subsystem that uses Agent0 hooks for lightweight observation capture, Agent0 scheduler for deferred processing, and Agent0 memory for durable learned knowledge.

This keeps normal hook execution fast and makes learned behavior persist in an Agent0-native way.

## Architecture

```text
EA0 hook bridge
  -> learning_capture
  -> observations.jsonl
  -> scheduled learning job
  -> learning_v1_process
  -> Agent0 memory
```

## Observation Sources

Primary sources:

- `PostToolUse`
- `Stop`
- optionally `SessionEnd`

The goal is to capture lightweight evidence, not to run expensive analysis inline.

## Observation Storage

Use plugin-owned state:

```text
usr/plugins/ea0-integration/state/learning/
├── observations.jsonl
├── checkpoints.json
└── status.json
```

Observation records should include:

- event name
- timestamp
- session id when available
- source agent
- tool name or operation identity
- success or failure summary
- project identity
- compact context snippet

## Scheduler Job

Add a scheduled learning processor that:

1. loads unprocessed observations
2. groups them by project and session
3. extracts reusable patterns
4. writes learned patterns into Agent0 memory
5. updates checkpoints safely

The scheduler is responsible for deferred analysis, not the hooks.

## Extraction Model

Initial v1 pattern classes:

- repeated successful workflow
- user correction pattern
- workaround pattern
- debugging technique
- project convention

The v1 extractor should be conservative and deterministic where possible.

## Memory Mapping

Recommended targets:

- `FRAGMENTS` for lightweight learned patterns and conventions
- `SOLUTIONS` for stronger repeatable workflows

Each learned memory entry should include metadata such as:

- `source: ea0-learning-v1`
- `scope: project|global`
- `project_id`
- `project_name`
- `confidence`
- `evidence_count`

## Project Scope

Learning must preserve project identity.

Each observation and resulting memory entry should record project metadata so later promotion logic can distinguish project-local behavior from globally reusable behavior.

## Failure Model

- hook capture failures must not block the main hook flow
- scheduler failures must be retry-safe
- malformed observations must be skipped rather than aborting the full batch

## Suggested Module Layout

Potential implementation layout:

```text
runtime/python/helpers/ea0_sync/
  learning_capture.py
  learning_store.py
  learning_v1_process.py
  learning_memory_adapter.py
  learning_project_scope.py
```

## Future Work

This design intentionally leaves room for:

- v2 instincts
- confidence decay
- promotion from learned patterns into generated skills, agents, and commands
- richer clustering and scoring
