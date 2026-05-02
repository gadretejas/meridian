# Six Domains Checklist

Use this checklist during Stage 2 (Plan) to systematically gather information for each domain. For each domain, collect the specified information, produce the output format, and avoid the listed mistakes.

## 1. Commands

**Collect:**
- Build command(s) with flags
- Test command(s) with flags
- Lint / format command(s)
- Dev server command
- Any other frequently used commands (deploy, migrate, seed, etc.)

**Output format:**
```
## Commands
- Build: `npm run build`
- Test: `pytest -v --cov=src`
- Lint: `ruff check --fix .`
- Dev: `npm run dev`
```

**Mistakes to avoid:**
- Listing tool names without the actual command (`"uses Jest"` instead of `npm test`)
- Omitting flags that affect behavior (`pytest` vs `pytest -v --tb=short`)
- Forgetting environment-specific commands (CI vs local)

**Questions to ask:**
- What commands do you run most often during development?
- Are there separate commands for CI vs local?
- Do any commands require specific environment variables?

## 2. Testing

**Collect:**
- Test framework and version
- Test file location and naming convention
- How to run a single test / test file
- Coverage expectations or thresholds
- Test events (unit, integration, e2e) and how to run each

**Output format:**
```
## Testing
- Framework: pytest 8.x
- Location: `tests/` mirroring `src/` structure
- Run all: `pytest`
- Run single: `pytest tests/test_auth.py::test_login`
- Coverage: ≥80% on `src/`, enforced in CI
```

**Mistakes to avoid:**
- Saying "write tests" without specifying framework or conventions
- Missing the single-test-run command (agents need this for iteration)
- Omitting test data setup or fixture patterns

**Questions to ask:**
- What test framework do you use?
- Where do test files live relative to source?
- Is there a coverage threshold enforced in CI?
- Do tests require setup (database, fixtures, mocks)?

## 3. Project Structure

**Collect:**
- Top-level directory layout
- Where source code lives
- Where tests live
- Where documentation lives
- Where configuration lives
- Any generated or vendor directories to ignore

**Output format:**
```
## Project Structure
- `src/` – Application source code
- `tests/` – Unit and integration tests
- `docs/` – Documentation
- `scripts/` – Build and utility scripts
- `dist/` – Build output (gitignored)
```

**Mistakes to avoid:**
- Describing the structure in prose instead of a scannable list
- Omitting generated directories that should not be edited
- Forgetting to mention monorepo structure if applicable

**Questions to ask:**
- What does your top-level directory layout look like?
- Are there generated directories the agent should never edit?
- Is this a monorepo? If so, how are packages organized?

## 4. Code Style

**Collect:**
- Language and version
- Naming conventions (files, variables, functions, classes)
- Formatting rules (indentation, line length, quotes)
- Import ordering conventions
- A real code snippet demonstrating the style
- Linter/formatter configuration

**Output format:**
```
## Code Style
- Language: TypeScript 5.x, strict mode
- Naming: camelCase for variables/functions, PascalCase for types/classes
- Formatting: Prettier with 2-space indent, single quotes, 100 char line
- Imports: external → internal → relative, alphabetical within groups

Example:
\```typescript
import { Router } from 'express';
import { UserService } from '@/services/user';
import { validateEmail } from './utils';

export async function createUser(req: Request): Promise<User> {
  const email = validateEmail(req.body.email);
  return UserService.create({ email });
}
\```
```

**Mistakes to avoid:**
- Describing style in prose without a code example
- Saying "follow best practices" (too vague for an agent)
- Omitting the linter/formatter config reference

**Questions to ask:**
- Can you share a code snippet that represents your ideal style?
- What linter/formatter do you use? Where is it configured?
- Any naming conventions the agent should follow strictly?

## 5. Git Workflow

**Collect:**
- Branch naming convention
- Commit message format
- PR requirements (reviewers, checks, squash policy)
- Protected branches
- Release process if relevant

**Output format:**
```
## Git Workflow
- Branches: `feature/<ticket>-<description>`, `fix/<ticket>-<description>`
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
- PRs: Require 1 approval, all CI checks passing, squash merge
- Protected: `main`, `release/*`
```

**Mistakes to avoid:**
- Omitting the commit message format (agents will invent one)
- Forgetting to mention squash vs merge policy
- Not specifying branch naming (agents default to arbitrary names)

**Questions to ask:**
- What branch naming convention do you follow?
- What commit message format do you prefer?
- What are your PR merge requirements?
- Are any branches protected?

## 6. Boundaries

**Collect:**
- Actions the agent should always do without asking
- Actions requiring human approval first
- Actions the agent must never take
- Specific files, directories, or configurations that are off-limits

**Output format:**
```
## Boundaries

### Always (do without asking)
- Run tests before committing
- Follow the naming conventions in Code Style
- Use existing utilities instead of reimplementing

### Ask First (get approval before)
- Adding new dependencies
- Changing database schema
- Modifying CI/CD configuration
- Deleting files

### Never (hard stops)
- Commit secrets, API keys, or credentials
- Edit `node_modules/`, `vendor/`, or generated files
- Disable or delete failing tests
- Push directly to `main`
```

**Mistakes to avoid:**
- Having only a "Never" list without "Always" and "Ask First"
- Being too generic ("don't break things")
- Missing the most common constraint: never commit secrets

**Questions to ask:**
- What should the agent always do without asking?
- What actions require your approval first?
- What should the agent never do, no matter what?
- Are there specific files or directories that are off-limits?
