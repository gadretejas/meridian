export const PROJECT_MD = `# Project: {{PROJECT_NAME}}

## Overview
<!-- One paragraph description of this project -->

## Tech Stack
| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| Frontend | | | |
| Backend | | | |
| Database | | | |
| Infra | | | |

## Conventions

### Code Style
<!-- Link to linter configs or style guides -->

### Naming
- Files: \`snake_case\`
- Classes: \`PascalCase\`
- Functions: \`snake_case\`
- Constants: \`UPPER_SNAKE\`

### Git
- Branch: \`{type}/{ticket}-{description}\`
- Commit: \`{type}({scope}): {message}\`

### Testing
- Minimum coverage: 80%
- Required for: All new code

## Architecture Patterns
<!-- Document key patterns used -->

## Security Requirements
<!-- Document security constraints -->

## Active Features
| Feature | Status | Spec |
|---------|--------|------|
| | | |
`;

export const SPEC_MD = `# {Feature Name}

## Overview
<!-- One paragraph summary of the feature -->

## Purpose
<!-- Single sentence: What problem does this solve? -->

## User Stories

### US-1: {Story Title}
**As a** {role}
**I want** {capability}
**So that** {benefit}

#### Acceptance Criteria
- [ ] **AC-1.1:** GIVEN {precondition} WHEN {action} THEN {expected result}
- [ ] **AC-1.2:** GIVEN {precondition} WHEN {action} THEN {expected result}

### US-2: {Story Title}
**As a** {role}
**I want** {capability}
**So that** {benefit}

#### Acceptance Criteria
- [ ] **AC-2.1:** GIVEN {precondition} WHEN {action} THEN {expected result}

## Functional Requirements

### REQ-F1: {Requirement Name}
The system **SHALL** {required behavior}.

### REQ-F2: {Requirement Name}
The system **MUST** {mandatory constraint}.

## Non-Functional Requirements

### REQ-NF1: Performance
The system **SHALL** respond within {X}ms for {operation}.

### REQ-NF2: Security
The system **MUST** {security constraint}.

## Constraints
- {Technical constraint}
- {Business constraint}

## Dependencies
- {External system/API}
- {Upstream feature}

## Out of Scope
- {Explicitly excluded functionality}
- {Future consideration}

## Open Questions
- [ ] {Decision needed}
- [ ] {Clarification needed}
`;

export const PLAN_MD = `# Implementation Plan: {Feature Name}

## Summary
<!-- One paragraph technical approach -->

## Architecture Decision
**Approach:** {chosen approach}
**Alternatives considered:** {rejected options}
**Rationale:** {why this approach}

## Technology Stack
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| {component} | {tech} | {ver} | {why} |

## Data Model

### New Entities
\`\`\`
{EntityName}
├── id: UUID (PK)
├── field: Type
├── created_at: Timestamp
└── FK: related_entity_id
\`\`\`

### Schema Changes
\`\`\`sql
-- Migration: {description}
ALTER TABLE {table} ADD COLUMN {column} {type};
CREATE INDEX {index} ON {table}({column});
\`\`\`

## API Contracts

### {Endpoint Name}
\`\`\`
{METHOD} /api/v1/{resource}

Request:
{
  "field": "type"
}

Response (200):
{
  "id": "uuid",
  "field": "value"
}

Errors:
- 400: Validation error
- 401: Unauthorized
- 404: Not found
\`\`\`

## Implementation Phases

### Phase 1: {Name} ({estimate})
- {Component 1}
- {Component 2}

**Deliverable:** {what's working at end}

### Phase 2: {Name} ({estimate})
- {Component 3}

**Depends on:** Phase 1
**Deliverable:** {what's working at end}

## Testing Strategy
| Level | Scope | Tools |
|-------|-------|-------|
| Unit | {scope} | {tool} |
| Integration | {scope} | {tool} |
| E2E | {scope} | {tool} |

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {risk} | H/M/L | H/M/L | {strategy} |

## Success Criteria
- [ ] All acceptance criteria pass
- [ ] Performance targets met
- [ ] No P0/P1 bugs
- [ ] Documentation updated
`;

export const TASKS_YAML = `# Tasks for {Feature Name}
feature: feature-name

phases:
  - id: 1
    name: Phase Name
    checkpoint: Validation criteria before Phase 2
    tasks:
      - id: "1.1"
        title: Task Title
        files:
          - path/to/file.ext
        depends: []
        estimate: 2h
        notes: Implementation hints
        parallel: false
        blocked: false
        subtasks:
          - text: Subtask description
            done: false
          - text: "Tests: test description"
            done: false

      - id: "1.2"
        title: Task Title (parallel)
        files:
          - path/to/file.ext
        depends: []
        parallel: true
        subtasks:
          - text: Subtask description
            done: false
          - text: "Tests: test description"
            done: false

  - id: 2
    name: Phase Name
    checkpoint: Feature functional end-to-end
    tasks:
      - id: "2.1"
        title: Task Title
        files:
          - path/to/file.ext
        depends:
          - "1.1"
          - "1.2"
        subtasks:
          - text: Subtask description
            done: false
          - text: "Tests: test description"
            done: false
`;
