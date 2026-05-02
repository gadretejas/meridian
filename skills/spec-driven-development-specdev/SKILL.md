---
name: specdev
description: Specification-driven development workflow for AI agents. Use when tasks are too large for a single session, require multi-step implementation, span multiple files/features, or need persistent requirements tracking.
---

# Spec-Driven Development

A CLI tool for managing structured specifications that persist across sessions, with JSON output designed for AI agents.

## 1. CLI Discovery

The CLI is located at `./scripts/specdev-cli/` relative to this SKILL.md file.

| Platform         | Script        |
| ---------------- | ------------- |
| Unix/Linux/macOS | `specdev`     |
| Windows          | `specdev.ps1` |

**Claude Code:** Use `${CLAUDE_PLUGIN_ROOT}/skills/specdev/scripts/specdev-cli/specdev` (or `specdev.ps1` on Windows).

## 2. Commands

| Command           | Description                                      |
| ----------------- | ------------------------------------------------ |
| `init`            | Initialize `.specs/` structure (idempotent)      |
| `new <name>`      | Create new spec with templates                   |
| `list`            | List all active specs and progress               |
| `context <spec>`  | Get spec context (`--level min\|standard\|full`) |
| `path <spec>`     | Get spec directory path                          |
| `archive <spec>`  | Move completed spec to archived                  |
| `validate <path>` | Check spec file completeness                     |
| `hook <event>`    | Run hook for event                               |

## 3. Workflows

### 3.1 Creating Specs

Use when starting a new feature or complex task.

1. Run `specdev init` (if no `.specs/` exists)
2. Run `specdev new <name>` to create spec structure with templates
3. Write draft `spec.md`, `plan.md`, and `tasks.yaml` based on initial understanding
4. Use `AskUserQuestion` to clarify ambiguities or validate assumptions
5. Update spec files to reflect user answers
6. Repeat steps 4-5 until spec is complete and clear
7. Run `specdev validate <name>` to verify spec structure
8. Present spec to user for final review before implementation

**Tip:** Always include verification methods in tasks (tests, assertions, manual checks). This creates feedback loops that catch errors early. Ask user for preferred verification approach if unclear.

### 3.2 Implementing Specs

Use when working on an existing spec.

1. Run `specdev list` to see active specs
2. Run `specdev context <spec> --level standard` to get current task
3. Read referenced files, implement the task
4. Run tests, verify implementation
5. Update `tasks.yaml` - mark task `done: true`
6. Repeat from step 2 until all tasks complete
7. Run `specdev archive <spec>` when 100% complete

## References

Templates and patterns available in `references/` directory:

- `spec-template.md` - Specification format
- `plan-template.md` - Planning format
- `tasks-template.md` - Task breakdown format
- `patterns.md` - Best practices
