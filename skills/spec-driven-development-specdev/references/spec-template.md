# Spec Template

Template for `.specs/active/{spec}/spec.md`.

## Template

```markdown
# {Feature Name}

## Purpose
One-line description of what this delivers.

## User Stories

### US-1: {Story Title}
AS A {role} I WANT {capability} SO THAT {benefit}

#### Acceptance Criteria
- [ ] GIVEN {context} WHEN {action} THEN {outcome}
- [ ] GIVEN {context} WHEN {action} THEN {outcome}

### US-2: {Story Title}
AS A {role} I WANT {capability} SO THAT {benefit}

#### Acceptance Criteria
- [ ] GIVEN {context} WHEN {action} THEN {outcome}

## Requirements

### REQ-1: {Requirement Title}
The system SHALL {behavior}.

### REQ-2: {Requirement Title}
The system MUST {constraint}.

### REQ-3: {Requirement Title}
The system SHOULD {preference}.

## Out of Scope
- {Explicitly excluded item 1}
- {Explicitly excluded item 2}

## Open Questions
- [ ] {Unresolved decision 1}
- [ ] {Unresolved decision 2}
```

## User Story Format

```
AS A {role}           # Who benefits
I WANT {capability}   # What they need
SO THAT {benefit}     # Why it matters
```

## Acceptance Criteria Format

```
GIVEN {precondition}  # Starting state
WHEN {action}         # User/system action
THEN {outcome}        # Expected result
```

### Examples

```markdown
- [ ] GIVEN valid credentials WHEN user submits login THEN JWT issued
- [ ] GIVEN invalid password WHEN user submits login THEN 401 returned
- [ ] GIVEN 5 failed attempts WHEN user submits login THEN account locked
```

## RFC 2119 Keywords

| Keyword | Meaning |
|---------|---------|
| SHALL | Absolute requirement |
| MUST | Absolute constraint (often security/compliance) |
| SHOULD | Recommended but not mandatory |
| MAY | Optional behavior |

### Examples

```markdown
### REQ-1: Password Storage
The system MUST hash passwords using bcrypt with cost factor >= 12.

### REQ-2: Session Duration
The system SHALL expire sessions after 24 hours of inactivity.

### REQ-3: Rate Limiting
The system SHOULD implement rate limiting on authentication endpoints.
```

## Common Clarifications

Use `AskUserQuestion` to resolve before writing spec:

- User roles and permissions model
- Edge cases and error scenarios
- Priority between conflicting requirements
- Scope boundaries (what's explicitly out)
- Performance/scaling expectations
- Integration points with external systems
