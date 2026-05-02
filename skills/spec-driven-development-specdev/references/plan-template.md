# Plan Template

Template for `.specs/active/{spec}/plan.md`.

## Template

```markdown
# Implementation Plan: {Feature}

## Technical Approach
{High-level architecture decision and rationale. 2-3 sentences explaining the chosen approach and why.}

## Stack/Dependencies
- {framework}: {version} - {purpose}
- {library}: {version} - {purpose}
- {tool}: {version} - {purpose}

## Data Model
{Schema changes, new models, database modifications}

```sql
-- Example: New tables or modifications
CREATE TABLE feature_table (
    id UUID PRIMARY KEY,
    ...
);
```

## API Contracts
{Endpoint definitions, request/response shapes}

```
POST /api/v1/resource
Request:  { field: type }
Response: { field: type }
```

## Implementation Phases

### Phase 1: {Name}
{Description of what this phase delivers}
- Component A
- Component B

### Phase 2: {Name}
{Description, noting dependencies on Phase 1}
- Component C (requires Phase 1 complete)
- Component D

### Phase 3: {Name}
{Final integration and polish}
- Integration testing
- Documentation

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| {risk description} | H/M/L | {strategy} |
| {risk description} | H/M/L | {strategy} |

## Open Decisions
- [ ] {Decision needed during implementation}
```

## Before Planning Checklist

1. **Explore codebase** using `Task` with `subagent_type=Explore`:
   - Existing patterns and conventions
   - Related components and interfaces
   - Current architecture and data flow
   - Files that will be affected

2. **Surface ambiguities** by reviewing:
   - Authentication/authorization model
   - Error handling strategy
   - Performance constraints
   - Integration boundaries

3. **Clarify with user** using `AskUserQuestion` if exploration reveals:
   - Architectural decisions needing input
   - Multiple valid approaches
   - Unclear requirements

## Phase Planning Guidelines

- Each phase should be independently deployable if possible
- Phase 1: Foundation (models, core logic)
- Phase 2: Features (API, business logic)
- Phase 3: Integration (UI, external systems)
- Include checkpoint criteria between phases

## Risk Assessment

| Impact | Description |
|--------|-------------|
| H (High) | Blocks release, security issue, data loss risk |
| M (Medium) | Degrades functionality, workaround exists |
| L (Low) | Minor inconvenience, cosmetic issue |
