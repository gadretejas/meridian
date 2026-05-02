# Boundary Patterns

Concrete three-tier boundary examples for different project types. Use these as starting points when helping users define boundaries in their SPEC.md. Adapt to the specific project — never copy generic patterns verbatim.

## Web Application (React / Next.js)

### Always
- Run `npm test` before committing
- Use existing UI components from `src/components/ui/` before creating new ones
- Follow the established API route naming convention
- Include TypeScript types for all props and API responses

### Ask First
- Adding new npm dependencies
- Changing database schema or migrations
- Modifying authentication/authorization logic
- Altering shared layout or navigation components
- Changing environment variable configuration

### Never
- Commit `.env.local` or any secrets
- Edit files in `node_modules/` or `.next/`
- Disable TypeScript strict mode or ESLint rules
- Push directly to `main` or `production` branches
- Remove or skip failing tests

## CLI Tool (Python)

### Always
- Run `pytest` before committing
- Include `--help` text for every new command and option
- Use `typer` / `click` for argument parsing (whichever the project uses)
- Write at least one test per new command

### Ask First
- Adding new Python dependencies to `pyproject.toml`
- Changing the CLI's public interface (command names, option names)
- Modifying output format (users may depend on parseable output)
- Changing default configuration file locations

### Never
- Commit secrets or hardcoded API keys
- Write to filesystem paths without user confirmation
- Execute shell commands without explicit user opt-in
- Break backward compatibility of existing commands silently
- Edit generated files in `dist/` or `build/`

## Data Pipeline (Python / SQL)

### Always
- Validate data schemas at pipeline boundaries
- Log pipeline step start/end with row counts
- Run data quality checks after transformation steps
- Use parameterized queries (never string interpolation for SQL)

### Ask First
- Changing source or sink table schemas
- Modifying scheduling or orchestration configuration
- Adding new data sources or external API connections
- Changing data retention or partitioning strategy

### Never
- Commit database credentials or connection strings
- Run `DROP TABLE` or `DELETE` without `WHERE` clause
- Modify production database directly (use migrations)
- Disable data validation checks
- Process PII without encryption or masking

## Mobile App (React Native / Flutter)

### Always
- Run lint and tests before committing
- Test on both iOS and Android simulators
- Follow platform-specific UI guidelines (Material / HIG)
- Use existing navigation patterns from the project

### Ask First
- Adding native modules or platform-specific code
- Changing the app's permission requirements
- Modifying deep linking or push notification configuration
- Upgrading React Native / Flutter major versions

### Never
- Commit signing keys, keystores, or provisioning profiles
- Hardcode API endpoints (use environment configuration)
- Disable ProGuard / code obfuscation in release builds
- Push directly to release branches

## API Service (Node.js / Express / Fastify)

### Always
- Validate request payloads at the controller layer
- Return consistent error response format
- Write integration tests for new endpoints
- Log errors with structured context (request ID, user ID)

### Ask First
- Adding new middleware to the request pipeline
- Changing authentication or rate-limiting configuration
- Modifying database indexes or adding migrations
- Introducing new external service dependencies

### Never
- Commit secrets, tokens, or API keys
- Return stack traces in production error responses
- Disable CORS, CSRF, or security headers
- Execute raw SQL with user-provided input
- Modify production infrastructure configuration
