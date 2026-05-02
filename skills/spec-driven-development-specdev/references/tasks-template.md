# Tasks Template

Template for `.specs/active/{spec}/tasks.yaml`.

## Template

```yaml
feature: feature-name

phases:
  - id: 1
    name: Phase Name
    checkpoint: Validation criteria before next phase
    tasks:
      - id: "1.1"
        title: Task Title
        files: [src/path/file.ts]
        depends: []
        notes: Implementation hints or context
        subtasks:
          - text: Implement core logic
            done: false
          - text: Add unit tests
            done: false
          - text: Update types/interfaces
            done: false

      - id: "1.2"
        title: Another Task
        files: [src/path/other.ts, src/path/related.ts]
        depends: []
        parallel: true  # Can run alongside 1.1
        subtasks:
          - text: Implementation
            done: false
          - text: Tests
            done: false

  - id: 2
    name: Next Phase
    checkpoint: All Phase 1 tasks complete, tests passing
    tasks:
      - id: "2.1"
        title: Dependent Task
        files: [src/path/file.ts]
        depends: ["1.1", "1.2"]  # Blocked until these complete
        subtasks:
          - text: Implementation
            done: false
          - text: Integration tests
            done: false
```

## Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `feature` | Yes | Feature identifier (kebab-case) |
| `phases[].id` | Yes | Phase number (1, 2, 3...) |
| `phases[].name` | Yes | Human-readable phase name |
| `phases[].checkpoint` | No | Validation criteria before next phase |
| `tasks[].id` | Yes | Task ID (format: "phase.task") |
| `tasks[].title` | Yes | Brief task description |
| `tasks[].files` | Yes | Files to be modified |
| `tasks[].depends` | No | Task IDs that must complete first |
| `tasks[].parallel` | No | `true` if can run with siblings |
| `tasks[].notes` | No | Implementation hints |
| `subtasks[].text` | Yes | Subtask description |
| `subtasks[].done` | Yes | Completion status |

## Task Granularity Guidelines

**Good task size:**
- 1-2 files modified
- <100 lines changed
- Completable in one focused session
- Clear "done" criteria

**Too large (split it):**
- 3+ files
- Multiple unrelated changes
- Vague completion criteria

**Too small (combine):**
- Single line change
- Trivial rename
- Whitespace-only

## Dependency Patterns

### Sequential (default)
```yaml
- id: "1.1"
  depends: []
- id: "1.2"
  depends: ["1.1"]  # Waits for 1.1
```

### Parallel
```yaml
- id: "1.1"
  depends: []
- id: "1.2"
  depends: []
  parallel: true  # Runs with 1.1
```

### Fan-out / Fan-in
```yaml
- id: "1.1"  # Foundation
  depends: []
- id: "1.2"  # Branch A
  depends: ["1.1"]
  parallel: true
- id: "1.3"  # Branch B
  depends: ["1.1"]
  parallel: true
- id: "1.4"  # Merge
  depends: ["1.2", "1.3"]
```

## Subtask Patterns

### Standard Pattern
```yaml
subtasks:
  - text: Implement core logic
    done: false
  - text: Add unit tests
    done: false
  - text: Update documentation
    done: false
```

### With Validation
```yaml
subtasks:
  - text: Implement feature
    done: false
  - text: Add tests (>80% coverage)
    done: false
  - text: Run linter, fix issues
    done: false
  - text: Manual verification
    done: false
```

## Marking Progress

Edit `tasks.yaml` directly to mark subtasks complete:

```yaml
subtasks:
  - text: Implement core logic
    done: true   # Changed from false
  - text: Add unit tests
    done: false  # Still pending
```

Use `spec status` to verify progress updates.
