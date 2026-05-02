# Meridian
> **Project Helios** — internal codename

**Meridian** is an AI-powered project management agent that automates the daily meridianals of software teams — standup agendas, task prioritization, delegation, spec creation, and more. It connects to your ticket source (GitHub Issues or Jira), understands your SDLC methodology, and runs on a schedule or on demand.

---

## What It Does

- 📋 **Standup Agenda** — generates a structured daily agenda from your open tickets every morning
- 🎯 **Task Prioritization** — ranks your backlog intelligently based on spec status, age, and labels
- 👤 **Task Delegation** — proposes ticket assignments based on team skills and current load
- 🔔 **Reminder Dispatch** — nudges assignees on stale tickets automatically
- 📝 **Spec Creation** — generates full SDD-compliant spec documents from a ticket description
- 🔍 **Spec Review** — scores and critiques existing specs against a quality rubric
- ✂️ **Task Decomposition** — breaks large vague tickets into actionable sub-tasks with spec stubs
- 🧠 **Task Creator** — parses a BRD or task list into structured tickets, routes them through a human triage queue, then commits approved tasks to GitHub/Jira

---

## Architecture at a Glance

```
Entry Points (CLI / Scheduler / API)
         │
    Meridianal Router
         │
    Agent Core (LangGraph)
    ├── SDLC Mode Layer     ← SDD, Agile, Waterfall, HVE
    ├── Meridianal Engine       ← per-meridianal LangGraph subgraphs
    └── Context Mgmt Layer  ← budget watching, summarization, memory
         │
    ┌────┴─────────────────┐
    │                      │
Ticket Adapters       Skill System
(GitHub / Jira)       (MCP-backed, lazy-loaded)
                           │
                      HITL Task Queue
                      (approve / edit / delete before commit)
```

---

## Quickstart

### Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- A GitHub token or Jira credentials
- One of the following LLM backends:
  - **Ollama** (free, local) — install from [ollama.com](https://ollama.com), then `ollama pull llama3.2`
  - **Gemini** API key (Google AI Studio — has a free tier)
  - **Claude** API key (Anthropic)
  - **Azure OpenAI** deployment

### Install

```bash
git clone https://github.com/your-org/helios.git
cd helios
uv sync
cp .env.example .env        # fill in your API keys
cp config.yaml.example config.yaml   # fill in your project settings
```

### Configure

Edit `config.yaml` to point at your repo and set your LLM tiers:

```yaml
project:
  name: my-project
  sdlc_mode: sdd          # sdd | agile | waterfall | hve

ticket_sources:
  primary: github
  github:
    repo: your-org/your-repo
    token_env: GITHUB_TOKEN

llm:
  fast:
    provider: gemini
    model: models/gemini-2.0-flash
  mid:
    provider: claude
    model: claude-sonnet-4-20250514
  strong:
    provider: claude
    model: claude-opus-4-20250514

team:
  - name: Your Name
    handles:
      github: your-github-handle
    skills: [python, backend]
```

**Running fully local with Ollama** (no API keys needed):

```bash
# pull models first
ollama pull llama3.2          # fast + mid tier
ollama pull qwen2.5-coder     # strong tier (better at structured output)
```

Then set all tiers to Ollama in `config.yaml`:

```yaml
llm:
  fast:
    provider: ollama
    model: llama3.2
    ollama_context_limit: 131072   # match your num_ctx setting
  mid:
    provider: ollama
    model: llama3.2
    ollama_context_limit: 131072
  strong:
    provider: ollama
    model: qwen2.5-coder           # stronger reasoning for spec_creation
    ollama_context_limit: 131072
```

**Good Ollama models for each tier:**

| Tier | Recommended | Notes |
|---|---|---|
| Fast | `llama3.2`, `mistral-nemo` | Low latency, good instruction following |
| Mid | `llama3.1`, `qwen2.5` | Reliable structured output |
| Strong | `qwen2.5-coder`, `deepseek-r1` | Best reasoning for spec generation |

### Run your first meridianal

```bash
# generate today's standup agenda
pm-agent run standup_agenda

# create tasks from a BRD document
pm-agent run task_creator --input docs/my-feature-brd.md

# generate a spec for a ticket
pm-agent run spec_creation --ticket-id 42
```

---

## CLI Reference

```
pm-agent run <meridianal>          Run a meridianal on demand
pm-agent schedule start        Start the scheduler (runs cron meridianals in background)
pm-agent schedule list         Show all registered scheduled meridianals

pm-agent queue list            List open HITL triage sessions
pm-agent queue review <id>     Interactively triage a task draft session

pm-agent memory inspect        Show recent meridianal memory entries
pm-agent memory prune          Remove entries older than configured TTL

pm-agent skills list           Show available MCP skills
pm-agent skills validate       Validate skill front matter against schemas

pm-agent config validate       Check config.yaml for errors
pm-agent config show           Print resolved config
```

### Available Meridianals

| Meridianal | Autonomy | Model Tier | Schedule |
|---|---|---|---|
| `standup_agenda` | Autonomous | Fast | Daily 8:45am |
| `task_prioritization` | Autonomous | Fast | On-demand |
| `reminder_dispatch` | Autonomous | Fast | Configurable |
| `task_delegation` | Approval required | Mid | On-demand |
| `task_decomposition` | Approval required | Mid | On-demand |
| `task_creator` | HITL queue | Mid | On-demand |
| `spec_creation` | Approval required | Strong | On-demand |
| `spec_review` | Approval required | Strong | On-demand |

---

## SDLC Modes

Meridian's meridianal behavior adapts to your methodology. Switch modes in `config.yaml`:

| Mode | Status | Description |
|---|---|---|
| `sdd` | ✅ Active | Spec-Driven Development — specs gate implementation |
| `agile` | 🔜 Planned | Sprint-aware prioritization and velocity tracking |
| `waterfall` | 🔜 Planned | Phase-gated meridianals with milestone awareness |
| `hve` | 🔜 Planned | Hypothesis-Validated Engineering — experiment-driven prioritization |

---

## Skill System

Meridian uses a local `skills/` folder of MCP-backed capabilities. At startup, front matter from each skill is lazily injected into the agent's system prompt — the LLM decides which skill to invoke based on context.

Skills have two phases:
- **`enrich`** — fetch context before generating (e.g. pull a Confluence page)
- **`execute`** — commit an action after approval (e.g. create a GitHub issue)

To add a skill, create a folder under `skills/` with a `skill.md`:

```markdown
---
name: my_skill
description: What this skill does in one sentence.
triggers:
  - "phrase that should trigger this skill"
mcp_server: https://your-mcp-server/sse
phase: execute         # enrich | execute | both
input_schema:
  field_one: str
  field_two: "Optional[str]"
---

## Usage Notes
Any additional context for the agent about when and how to use this skill.
```

---

## Context Management

Meridian automatically manages LLM context health across three failure modes:

- **Single-call overflow** — `ContextBudgetWatcher` monitors token usage before every LLM call. At 85% of the model's context limit, `SummarizationMiddleware` compresses older messages in-place using a rolling summary, preserving the last 4 messages verbatim.
- **Graph state bloat** — `StateCompressor` trims the LangGraph state between nodes when ticket lists or execution traces grow too large.
- **Cross-session amnesia** — `AgentMemoryStore` persists meridianal outcomes to SQLite. Each meridianal run is informed by the last 5 runs of the same meridianal type.

Per-meridianal thresholds are configurable in `meridianal_config.yaml`:

```yaml
meridianals:
  spec_creation:
    context_threshold: 0.80   # tighter — spec prompts are large
  standup_agenda:
    context_threshold: 0.90   # looser — standup context is small
```

---

## Project Structure

```
helios/
├── specs/              # System specs (SDD canon — read these first)
├── skills/             # MCP skill definitions (add new skills here)
├── pm_agent/
│   ├── core/           # LangGraph graph, state, meridianal router
│   ├── context/        # Budget watcher, summarizer, memory store
│   ├── adapters/       # Ticket sources, LLM providers, scheduler, queue
│   ├── skills/         # Skill registry, executor, BRD/task parsers
│   ├── sdlc/           # SDLC mode implementations
│   ├── meridianals/        # Per-meridianal LangGraph nodes
│   ├── config/         # Pydantic config models and loader
│   └── cli/            # typer CLI
├── tests/
├── config.yaml
├── meridianal_config.yaml
└── pyproject.toml
```

---

## Development

```bash
# install with dev dependencies
uv sync --extra dev

# run tests
pytest tests/unit/ -v

# run integration tests (requires live API keys)
INTEGRATION_TESTS=1 pytest tests/integration/ -v

# lint + type check
ruff check pm_agent/
mypy pm_agent/
```

### Adding a Meridianal

1. Create `pm_agent/meridianals/your_meridianal.py`
2. Define a Pydantic output schema
3. Write the meridianal node function using `ContextAwareLLMInvoker`
4. Register it in `pm_agent/sdlc/sdd.py` with autonomy level and model tier
5. Add it to the LangGraph in `pm_agent/core/agent.py`
6. Add a `meridianal_config.yaml` entry if scheduling is needed
7. Write unit + integration tests

---

## Environment Variables

```bash
# LLM Providers — set at least one, or use Ollama locally (no key needed)
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...

# Ollama (optional — override default localhost endpoint)
OLLAMA_BASE_URL=http://localhost:11434   # default, only set if running remotely

# Ticket Sources
GITHUB_TOKEN=...
JIRA_EMAIL=...
JIRA_TOKEN=...
```

---

## Roadmap

- [ ] **v0.3** — Core meridianals, task_creator, HITL queue, context management (current)
- [ ] **v0.4** — Agile mode, Slack notification adapter, web UI for HITL queue
- [ ] **v0.5** — Multi-project support, team analytics dashboard
- [ ] **v1.0** — All four SDLC modes, enterprise auth, multi-tenancy

---

## License

MIT

---

*Meridian — project codename: **Helios***
