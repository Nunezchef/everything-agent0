# Capability: ECC Agent Transformer

## ADDED Requirements

### Requirement: Transform ECC agents into Agent0 agent directories

Ea0 MUST transform ECC markdown agents from `agents/*.md` into valid Agent0 agent directories under `usr/agents/`.

#### Scenario: Generate an Agent0 agent from an ECC markdown agent

- **WHEN** Ea0 sync processes an ECC agent file with valid frontmatter and body
- **THEN** it SHALL generate an Agent0 agent directory under `usr/agents/ea0-<normalized-name>/`
- **AND** it SHALL generate an `agent.json` file in that directory
- **AND** it SHALL generate a `_context.md` file in that directory

### Requirement: Preserve ECC agent metadata

Ea0 MUST preserve important ECC agent metadata during transformation.

#### Scenario: Preserve tool and model metadata

- **WHEN** an ECC agent defines `tools` or `model` in frontmatter
- **THEN** Ea0 SHALL record the original values in plugin state metadata
- **AND** unmapped tools SHALL be preserved without blocking generation

### Requirement: Map ECC tools to Agent0 capability metadata

Ea0 MUST convert known ECC tool names into Agent0 capability metadata.

#### Scenario: Known ECC tool names are mapped

- **WHEN** an ECC agent includes known tools such as `Read`, `Write`, `Edit`, `Grep`, `Glob`, or `Bash`
- **THEN** Ea0 SHALL map them to Agent0 capability metadata
- **AND** the generated metadata SHALL include the mapped capability list

#### Scenario: Unknown ECC tool names are not fatal

- **WHEN** an ECC agent includes an unrecognized tool name
- **THEN** Ea0 SHALL still generate the Agent0 agent
- **AND** it SHALL record a transformation warning for that tool

### Requirement: Generated agents must be discoverable by Agent0

Ea0 MUST generate agent outputs in the format required by Agent0 agent discovery.

#### Scenario: Generated agent appears as a selectable profile

- **WHEN** Ea0 sync completes successfully
- **THEN** generated EA0 agents SHALL be discoverable from `usr/agents/*`
- **AND** Agent0 SHALL be able to load the generated `agent.json`
- **AND** the generated profile SHALL be eligible to appear in the Agent Settings dropdown

### Requirement: Transformation must degrade gracefully

Ea0 MUST degrade gracefully when ECC agent inputs are incomplete or malformed.

#### Scenario: Missing frontmatter

- **WHEN** an ECC agent file has missing or malformed frontmatter
- **THEN** Ea0 SHALL derive a generated name from the filename
- **AND** it SHALL attempt to derive a title from the first H1 or filename
- **AND** it SHALL record a transformation warning
- **AND** it SHALL continue generation unless the file body is unusable
