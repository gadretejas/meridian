# Patterns & Best Practices

## Core Principles

1. **Spec first** - Never implement without written requirements
2. **Small tasks** - Each task fits in one context window
3. **Explicit dependencies** - Mark what blocks what
4. **Checkpoint often** - Save progress every 2-3 tasks
5. **Separate concerns** - Spec (what) vs Plan (how) vs Tasks (when)

## Token Optimization

### Spec Loading Strategy

**Always load** (minimal context):
- `project.md` (conventions only)
- `tasks.yaml` (current phase only)

**Load on demand:**
- `spec.md` → When clarifying requirements
- `plan.md` → When making technical choices
- `design.md` → When architecting

### Compact Spec Notation

For token-constrained contexts, use compact acceptance criteria:

```markdown
## US-1: User Login
AC: [valid-creds→JWT] [invalid→401] [lockout@5-fails]
REQ: SHALL issue JWT on success, MUST hash passwords bcrypt
```

### Compact Task Reference

```
TASK 1.1: Setup auth module [src/auth.ts]
  [x] Implement JWT signing
  [ ] Add refresh token logic
  [ ] Unit tests
```

## Progress Checkpoints

Save progress at session end or after significant milestones:

```markdown
<!-- .specs/active/{spec}/checkpoint.md -->
## Session: {date}
- Completed: 1.1, 1.2, 1.3
- Next: 2.1
- Blockers: None
- Notes: {Context for next session}
```

## Context Level Selection

| Situation | Level | Command |
|-----------|-------|---------|
| Familiar spec, continuing work | `min` | `spec context {spec} --level min` |
| Standard implementation | `standard` | `spec context {spec}` |
| First time, need full picture | `full` | `spec context {spec} --level full` |

## When to Use Tools

| Situation | Tool |
|-----------|------|
| Unclear requirements | `AskUserQuestion` |
| Need to understand codebase | `Task` with `subagent_type=Explore` |
| Complex implementation planning | `Task` with `subagent_type=Plan` |
| Making assumptions | `AskUserQuestion` (ask first) |

**Principle:** Ask early, explore thoroughly.

## Common Patterns

### Starting a New Spec

```bash
spec new {name}           # Creates spec directory with templates
# Edit spec.md            # Define requirements
# Edit plan.md            # Technical approach
# Edit tasks.yaml         # Task breakdown
spec validate {spec}      # Check completeness
```

### Resuming Work

```bash
spec status               # See all active specs
spec context {spec} --level min  # Get current task
# Implement...
# Edit tasks.yaml to mark done
spec status               # Verify progress
```

### Completing a Spec

```bash
spec status               # Should show 100% or "ready to archive"
spec archive {spec}       # Move to .specs/archived/
```

## Edge Cases

### Multiple Parallel Specs

- Use `spec status` to see all active specs
- Focus on one spec per session when possible
- If switching, always run `spec context` for the new spec

### Blocked Task

1. Document blocker in `checkpoint.md`
2. Use `AskUserQuestion` to get user decision
3. If external blocker, skip to next parallel task if available

### Spec Changes Mid-Implementation

1. Update `spec.md` with changes
2. Review impact on `plan.md`
3. Adjust `tasks.yaml` (add/remove/modify tasks)
4. Use `spec validate` to check consistency

### Failed Validation

If `spec validate` fails:
- Missing sections → Add required content
- Uncovered requirements → Add tasks for each REQ
- Circular dependencies → Fix `depends` field in tasks.yaml
