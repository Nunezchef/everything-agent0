# Proposal: Add EA0 Continuous Learning v1

## Summary

Implement EA0 continuous-learning v1 in Agent0 as a plugin-owned learning subsystem built on top of Agent0 hooks, scheduler, and memory.

## Problem

ECC continuous-learning currently assumes Claude-specific hooks and filesystem state such as `~/.claude/...`. Ea0 does not yet provide an Agent0-native replacement for this behavior.

Without a native learning subsystem:

- learned workflow patterns are not retained in Agent0 memory
- ECC continuous-learning skills remain partially documentary
- Ea0 cannot provide ongoing pattern extraction or reuse

## Goals

- capture lightweight learning observations from EA0 hook events
- process observations asynchronously using Agent0 scheduler
- store learned patterns in Agent0 memory
- preserve project-scoped learning metadata
- keep hook execution lightweight and non-blocking

## Non-Goals

- full v2 instinct clustering and evolution
- automatic generation of agents, skills, or commands
- replacing Agent0 core memory behavior
- copying ECC Claude filesystem storage patterns

## Proposed Change

Add a learning pipeline that:

1. captures structured observations from selected EA0 hook events
2. writes those observations into Ea0 plugin state
3. processes pending observations in a scheduled background job
4. stores extracted reusable patterns in Agent0 memory
5. stores stronger repeatable workflows as solution-like memory entries when appropriate

## User Impact

After this change:

- Ea0 will continuously learn project-specific patterns in Agent0-native storage
- learned workflows will survive across sessions
- continuous-learning v1 will become functional instead of purely documentary
- the architecture will support later v2 evolution on the same substrate

## Risks

- too much raw observation noise may reduce learning quality
- overly aggressive extraction could create low-value memory entries
- scheduler and hook coordination must remain non-blocking and idempotent

## Success Criteria

- live EA0 hooks produce structured learning observations
- scheduled processing converts pending observations into Agent0 memory entries
- learned entries preserve project-aware metadata
- normal agent execution continues even if learning capture or processing fails
