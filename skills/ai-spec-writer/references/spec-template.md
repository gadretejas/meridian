# SPEC.md Template

Use this template as the scaffold when generating a project's SPEC.md during Stage 3 (Tasks) and Stage 4 (Implement). Replace all `[placeholder]` text with project-specific content. Delete any sections marked optional if not applicable.

---

```markdown
# [Project Name] Specification

## Vision

[1-3 sentences: What is being built, for whom, and why. Focus on the user experience and the problem being solved.]

### Success Criteria

- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]
- [ ] [Measurable outcome 3]

## Tech Stack

- **Language:** [e.g., TypeScript 5.x, Python 3.12]
- **Framework:** [e.g., Next.js 14, FastAPI 0.110]
- **Database:** [e.g., PostgreSQL 16 with Prisma ORM]
- **Testing:** [e.g., pytest 8.x, Jest 29]
- **Package Manager:** [e.g., pnpm 9, uv]
- **Other:** [e.g., Redis for caching, Docker for deployment]

## Commands

```bash
# Build
[build command with flags]

# Test
[test command with flags]

# Lint / Format
[lint command]

# Dev Server
[dev command]

# Other (optional)
[deploy, migrate, seed, etc.]
```

## Testing

- **Framework:** [name and version]
- **Location:** [where test files live, e.g., `tests/` mirroring `src/`]
- **Run all:** `[command]`
- **Run single:** `[command for single test/file]`
- **Coverage:** [threshold, e.g., ≥80% on src/, enforced in CI]
- **Events:** [unit, integration, e2e — and how to run each]

### Test Conventions

[Optional: fixture patterns, mock strategies, test data setup]

## Project Structure

```
[project-root]/
├── [source dir]/       – [description]
├── [test dir]/         – [description]
├── [docs dir]/         – [description]
├── [config files]      – [description]
└── [other dirs]/       – [description]
```

### Key Files

- `[file]` – [purpose]
- `[file]` – [purpose]

## Code Style

- **Naming:** [conventions for files, variables, functions, classes]
- **Formatting:** [tool, config, indent, line length, quotes]
- **Imports:** [ordering convention]
- **Linter:** [tool and config location]

### Example

```[language]
[A real code snippet (10-20 lines) demonstrating the project's style:
 naming, formatting, imports, error handling, types]
```

## Git Workflow

- **Branches:** [naming convention, e.g., `feature/<ticket>-<desc>`]
- **Commits:** [format, e.g., Conventional Commits]
- **PRs:** [requirements: reviewers, checks, merge strategy]
- **Protected:** [branches that cannot be pushed to directly]

## Boundaries

### Always (do without asking)
- [action 1]
- [action 2]
- [action 3]

### Ask First (get approval before)
- [action 1]
- [action 2]
- [action 3]

### Never (hard stops)
- [action 1]
- [action 2]
- Never commit secrets, API keys, or credentials

## Architecture Notes (optional)

[High-level architecture description, diagrams, or key design decisions.
 Include only if the project has non-obvious architectural patterns.]

## Version History

| Version | Date       | Changes                |
|---------|------------|------------------------|
| 1.0     | [date]     | Initial specification  |
```

---

## Template Usage Notes

- **Vision** and **Boundaries** are the two most critical sections. Start with these.
- **Commands** must contain actual runnable commands with flags, not just tool names.
- **Code Style** must contain at least one real code snippet.
- Every section maps to one of the six core domains from the spec guideline.
- The template uses medium freedom: six domains are mandatory, content within each is flexible.
- Delete the `Architecture Notes` section if the project has straightforward architecture.
- Update `Version History` whenever the spec changes materially.
