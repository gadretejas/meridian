# PM Agent — Phase-by-Phase Implementation Plan
> Language: Python 3.11+ | Framework: LangChain / LangGraph | Status: ACTIVE

---

## How to Read This Document

Each phase is structured as:
- **Goal** — what capability exists at the end of this phase
- **Entry condition** — what must be true before this phase starts
- **Tasks** — ordered implementation steps with file targets and LangChain-specific notes
- **Verification** — how you know the phase is done (runnable checks, not vibes)
- **Exit condition** — the exact state of the system after this phase

Phases build strictly on each other. Never start Phase N+1 until Phase N's exit condition is met.

---

## Dependency Map

```
Phase 0 (Scaffold)
    │
    ├──► Phase 1 (Ticket Adapters)
    │         │
    │         └──► Phase 2 (LLM Router)
    │                   │
    │                   └──► Phase 3 (Context Mgmt)
    │                             │
    │              ┌──────────────┼──────────────┐
    │              │              │              │
    │         Phase 4        Phase 5        Phase 7 (SDD + Core Rituals)
    │        (Skills)      (HITL Queue)          │
    │              │              │              │
    │              └──────┬───────┘              │
    │                     │                      │
    │                Phase 6 (task_creator)       │
    │                                            │
    │                              Phase 8 (Remaining Rituals)
    │                                            │
    │                              Phase 9 (Scheduler)
    │                                            │
    │                              Phase 10 (CLI + API)
    │
    └──► (runs in parallel with all phases)
```

---

## Phase 0 — Scaffold & Config

**Goal**: A runnable Python project with validated config loading, correct folder structure, and all dependencies pinned. No agent logic yet — just the skeleton everything else will hang on.

**Entry condition**: Spec v0.3 reviewed and open questions OQ-1 through OQ-12 recorded (not necessarily resolved).

---

### Task 0.1 — Initialize project with `uv` and `pyproject.toml`

**File**: `pyproject.toml`

Use `uv` (faster than pip, deterministic lockfile, native Apple Silicon support on your M4).

```toml
[project]
name = "pm-agent"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # LangChain core
    "langchain>=0.3",
    "langchain-core>=0.3",
    "langgraph>=0.2",

    # LLM providers
    "langchain-google-genai>=2.0",
    "langchain-anthropic>=0.3",
    "langchain-openai>=0.2",        # for Azure OpenAI
    "langchain-ollama>=0.2",        # for local Ollama models (Llama, Mistral, etc.)

    # MCP
    "langchain-mcp-adapters>=0.1",

    # Ticket sources
    "PyGithub>=2.3",
    "atlassian-python-api>=3.41",

    # Document parsing
    "pypdf>=4.0",
    "python-docx>=1.1",

    # Scheduling
    "apscheduler>=3.10",

    # CLI
    "typer[all]>=0.12",

    # Config & validation
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",

    # Persistence
    "aiosqlite>=0.20",

    # Utilities
    "tenacity>=8.3",               # retry logic for API calls
    "rich>=13.7",                  # pretty CLI output
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.14",
    "respx>=0.21",                 # HTTP mocking for adapter tests
    "ruff>=0.4",
    "mypy>=1.10",
]

[project.scripts]
pm-agent = "pm_agent.cli.main:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
```

---

### Task 0.2 — Create folder scaffold

Run once to create all empty packages:

```bash
mkdir -p pm_agent/{core,context/memory,adapters/{ticket,llm,scheduler,approval,notification,queue},skills/parsers,sdlc,rituals,config}
mkdir -p skills/{github_create_issue,jira_create_ticket,confluence_search,notion_fetch_page,linear_fetch_issues}
mkdir -p specs tests/{unit,integration,fixtures} pm_agent/cli
touch pm_agent/__init__.py
# touch __init__.py in every pm_agent sub-package
find pm_agent -type d -exec touch {}/__init__.py \;
```

---

### Task 0.3 — Pydantic config models

**File**: `pm_agent/config/models.py`

Define every config shape as a Pydantic v2 `BaseModel`. These are the source of truth for `config.yaml` deserialization. Key models:

```python
class ModelTierConfig(BaseModel):
    provider: Literal["gemini", "claude", "azure_openai", "ollama"]
    model: str
    temperature: float = 0.3
    max_tokens: int = 4096
    base_url: Optional[str] = None          # Ollama: override default http://localhost:11434
    ollama_context_limit: Optional[int] = None  # Ollama: set to match your num_ctx value

class LLMConfig(BaseModel):
    fast: ModelTierConfig
    mid: ModelTierConfig
    strong: ModelTierConfig

class GitHubConfig(BaseModel):
    repo: str
    token_env: str = "GITHUB_TOKEN"

class JiraConfig(BaseModel):
    url: str
    email_env: str = "JIRA_EMAIL"
    token_env: str = "JIRA_TOKEN"

class TicketSourcesConfig(BaseModel):
    primary: Literal["github", "jira"]
    github: Optional[GitHubConfig] = None
    jira: Optional[JiraConfig] = None

class ContextManagementConfig(BaseModel):
    threshold: float = 0.85
    tail_window: int = 4
    summarizer_model: ModelTierConfig
    state_compressor: StateCompressorConfig
    memory_store: MemoryStoreConfig

class HITLQueueConfig(BaseModel):
    backend: Literal["in_process", "sqlite", "redis"] = "in_process"
    sqlite_path: str = "~/.pm-agent/queue.db"
    item_ttl_hours: int = 48

class TeamMemberConfig(BaseModel):
    name: str
    handles: dict[str, str]        # {"github": "...", "jira": "..."}
    skills: list[str] = []

class ProjectConfig(BaseModel):
    name: str
    sdlc_mode: Literal["sdd", "agile", "waterfall", "hve"] = "sdd"

class AppConfig(BaseModel):
    project: ProjectConfig
    ticket_sources: TicketSourcesConfig
    llm: LLMConfig
    scheduler: SchedulerConfig
    approval: ApprovalConfig
    notifications: NotificationsConfig
    hitl_queue: HITLQueueConfig
    context_management: ContextManagementConfig
    skills: SkillsConfig
    team: list[TeamMemberConfig] = []
```

> **LangChain note**: `ModelTierConfig` maps directly to the kwargs needed by `ChatGoogleGenerativeAI`, `ChatAnthropic`, and `AzureChatOpenAI`. Keep field names consistent so the LLM router can instantiate them without branching.

---

### Task 0.4 — Config loader

**File**: `pm_agent/config/loader.py`

```python
from functools import lru_cache
import yaml
from pathlib import Path
from pm_agent.config.models import AppConfig

@lru_cache(maxsize=1)
def load_config(config_path: str = "config.yaml") -> AppConfig:
    with open(Path(config_path)) as f:
        raw = yaml.safe_load(f)
    return AppConfig.model_validate(raw)
```

Singleton pattern — config is loaded once and cached. Every component calls `load_config()`.

---

### Task 0.5 — Ritual config loader

**File**: `pm_agent/config/ritual_loader.py`

Separate loader for `ritual_config.yaml`. Returns a `dict[str, RitualOverrideConfig]` keyed by ritual name. Ritual components merge this on top of SDLC mode defaults.

---

### Task 0.6 — `.env.example` and `config.yaml` stubs

Create `config.yaml` with placeholder values for every field in `AppConfig`. Create `.env.example` listing every `_env` referenced variable. Commit both. Never commit `.env`.

---

### Task 0.7 — Logging setup

**File**: `pm_agent/core/logging.py`

Configure `structlog` (or stdlib `logging` with JSON formatter) with:
- A `ritual_name` context var injected on every log line during ritual execution
- A `compression_event` flag that fires whenever `SummarizationMiddleware` triggers
- `rich` console handler for local dev, JSON handler for production

---

### Verification (Phase 0)

```bash
uv sync
python -c "from pm_agent.config.loader import load_config; print(load_config())"
pytest tests/ -q   # 0 tests, 0 failures — clean empty suite
```

**Exit condition**: Project installs cleanly, config loads without error against `config.yaml` stub, test suite runs (passes vacuously).

---

## Phase 1 — Ticket Source Adapters

**Goal**: The system can read tickets from GitHub Issues and Jira through a unified interface. No LLM involved yet — pure data layer.

**Entry condition**: Phase 0 complete. `GITHUB_TOKEN` and Jira credentials available in `.env`.

---

### Task 1.1 — Core data models

**File**: `pm_agent/adapters/ticket/models.py`

```python
from enum import StrEnum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal

class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"

class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TeamMember(BaseModel):
    name: str
    github_handle: Optional[str] = None
    jira_email: Optional[str] = None

class TicketSummary(BaseModel):
    """Compressed form used by StateCompressor."""
    id: str
    title: str
    status: TicketStatus
    priority: Priority

class Ticket(BaseModel):
    id: str
    title: str
    description: str
    status: TicketStatus
    priority: Priority
    assignee: Optional[TeamMember] = None
    labels: list[str] = []
    created_at: datetime
    updated_at: datetime
    source: Literal["github", "jira"]
    raw: dict = {}

class TicketFilter(BaseModel):
    status: Optional[list[TicketStatus]] = None
    assignee: Optional[str] = None
    labels: Optional[list[str]] = None
    updated_since: Optional[datetime] = None

class TicketSpec(BaseModel):
    """Input to create_ticket."""
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    labels: list[str] = []
    assignee: Optional[str] = None

class TicketDelta(BaseModel):
    """Fields to update on an existing ticket."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[Priority] = None
    assignee: Optional[str] = None
    labels: Optional[list[str]] = None
```

---

### Task 1.2 — `TicketSourceAdapter` ABC

**File**: `pm_agent/adapters/ticket/base.py`

```python
from abc import ABC, abstractmethod
from pm_agent.adapters.ticket.models import *

class TicketSourceAdapter(ABC):
    @abstractmethod
    async def list_tickets(self, filters: TicketFilter) -> list[Ticket]: ...

    @abstractmethod
    async def get_ticket(self, id: str) -> Ticket: ...

    @abstractmethod
    async def create_ticket(self, spec: TicketSpec) -> Ticket: ...

    @abstractmethod
    async def update_ticket(self, id: str, delta: TicketDelta) -> Ticket: ...

    @abstractmethod
    async def add_comment(self, id: str, body: str) -> None: ...

    @abstractmethod
    async def list_members(self) -> list[TeamMember]: ...
```

All methods are **async**. GitHub and Jira calls are I/O-bound — always await them.

---

### Task 1.3 — `GitHubIssuesAdapter`

**File**: `pm_agent/adapters/ticket/github.py`

- Use `PyGithub` in a thread pool executor (`asyncio.to_thread`) since PyGithub is sync
- Map GitHub issue fields to `Ticket`: `state` → `TicketStatus`, `labels` → list, `assignee.login` → `TeamMember`
- Parse `priority:high` / `priority:low` labels into `Priority` enum
- `create_ticket` → `repo.create_issue(title, body, labels, assignee)`
- Wrap all calls with `tenacity.retry` (exponential backoff, `RateLimitExceededException`)

**Priority label convention** (document in `README.md`):
GitHub has no native priority field. Use label convention `priority:critical`, `priority:high`, `priority:medium`, `priority:low`. The adapter reads/writes these transparently.

---

### Task 1.4 — `JiraAdapter`

**File**: `pm_agent/adapters/ticket/jira.py`

- Use `atlassian-python-api` (`Jira` class), also sync — wrap with `asyncio.to_thread`
- Map Jira `issuetype`, `status.name`, `priority.name` to enums
- `create_ticket` → `jira.create_issue(fields={...})`
- Handle Jira pagination in `list_tickets` (`startAt`, `maxResults`)
- Wrap with `tenacity.retry` for `requests.exceptions.ConnectionError` and 429s

---

### Task 1.5 — Adapter factory

**File**: `pm_agent/adapters/ticket/factory.py`

```python
def get_ticket_adapter(config: AppConfig) -> TicketSourceAdapter:
    source = config.ticket_sources.primary
    if source == "github":
        return GitHubIssuesAdapter(config.ticket_sources.github)
    elif source == "jira":
        return JiraAdapter(config.ticket_sources.jira)
    raise ValueError(f"Unknown ticket source: {source}")
```

---

### Task 1.6 — Unit tests with mocked APIs

**File**: `tests/unit/test_ticket_adapters.py`

- Mock `PyGithub` responses with `pytest-mock`
- Mock `atlassian` responses with `respx` or `unittest.mock`
- Test: `list_tickets` with filters, `create_ticket` round-trip, priority label parsing, `TicketStatus` mapping
- Test: `tenacity` retry fires on rate limit (mock `RateLimitExceededException`)

---

### Verification (Phase 1)

```bash
pytest tests/unit/test_ticket_adapters.py -v
# manually:
python -c "
import asyncio
from pm_agent.config.loader import load_config
from pm_agent.adapters.ticket.factory import get_ticket_adapter
cfg = load_config()
adapter = get_ticket_adapter(cfg)
tickets = asyncio.run(adapter.list_tickets(TicketFilter(status=['open'])))
print(f'{len(tickets)} open tickets fetched')
"
```

**Exit condition**: Both adapters pass unit tests. Manual smoke test returns tickets from a real repo/project.

---

## Phase 2 — LLM Provider Router

**Goal**: Any ritual can request a `fast`, `mid`, or `strong` model by tier name and get back a LangChain `BaseChatModel` instance for the configured provider. No LLM calls yet — just instantiation and routing.

**Entry condition**: Phase 0 complete. API keys for at least one cloud provider in `.env`, **or** Ollama running locally (`ollama serve`) with at least one model pulled (`ollama pull llama3.2`).

---

### Task 2.1 — `ModelConfig` resolution

**File**: `pm_agent/adapters/llm/resolver.py`

Resolution priority chain:
1. `ritual_config.yaml` `model_override` for this ritual
2. SDLC mode default tier mapping
3. Global `config.yaml` `llm.*` tier

```python
def resolve_model_config(
    ritual_name: str,
    tier: Literal["fast", "mid", "strong"],
    app_config: AppConfig,
    ritual_overrides: dict,
) -> ModelTierConfig:
    # check ritual-level override first
    override = ritual_overrides.get(ritual_name, {}).get("model_override")
    if override:
        return ModelTierConfig.model_validate(override)
    # fall back to global tier config
    return getattr(app_config.llm, tier)
```

---

### Task 2.2 — Provider factory

**File**: `pm_agent/adapters/llm/factory.py`

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI
from langchain_ollama import ChatOllama

def get_llm(config: ModelTierConfig) -> BaseChatModel:
    match config.provider:
        case "gemini":
            return ChatGoogleGenerativeAI(
                model=config.model,
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            )
        case "claude":
            return ChatAnthropic(
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        case "azure_openai":
            return AzureChatOpenAI(
                azure_deployment=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        case "ollama":
            return ChatOllama(
                model=config.model,                    # e.g. "llama3.2", "mistral", "qwen2.5-coder"
                temperature=config.temperature,
                num_predict=config.max_tokens,         # Ollama uses num_predict, not max_tokens
                base_url=config.base_url or "http://localhost:11434",
            )
        case _:
            raise ValueError(f"Unknown provider: {config.provider}")
```

> **LangChain note**: All four return `BaseChatModel`. The rest of the system never imports provider-specific classes — only `BaseChatModel`. This is the entire point of the factory.

> **Ollama note — structured output**: `ChatOllama` supports `.with_structured_output()` only for models that have reliable JSON mode. Llama 3.2, Mistral 7B, and Qwen 2.5 all work well. Avoid structured output with older or smaller models (< 7B) — they hallucinate schema compliance. If a ritual uses `get_structured_llm()` with an Ollama model and fails to parse, the retry in `structured.py` will attempt up to 3 times before raising.

> **Ollama note — token counting**: `ChatOllama` does not implement `get_num_tokens_from_messages()`. The `ContextBudgetWatcher` handles this gracefully — Stage 2 (provider API count) is skipped for Ollama and the character proxy estimate is used as the final value. This means the threshold may fire slightly earlier or later than with cloud models, but it will never silently overflow.

> **Ollama note — context limits**: Ollama model context limits vary by model and your `ollama run` configuration (`num_ctx`). Set `ollama_context_limit` in `config.yaml` to tell `ContextBudgetWatcher` the actual limit of your loaded model. Defaults to 8,192 if unset — conservative but safe.

---

### Task 2.3 — Structured output helper

**File**: `pm_agent/adapters/llm/structured.py`

Thin wrapper around `.with_structured_output()` with retry on parse failure:

```python
from tenacity import retry, stop_after_attempt, wait_fixed

def get_structured_llm(
    llm: BaseChatModel,
    schema: type[BaseModel],
    max_retries: int = 3,
) -> Runnable:
    """Returns a runnable that guarantees Pydantic output or raises after retries."""
    return llm.with_structured_output(schema, include_raw=True)
```

The `include_raw=True` flag lets you inspect the raw LLM output when structured parsing fails, which is essential for debugging.

---

### Task 2.4 — Unit tests

**File**: `tests/unit/test_llm_router.py`

- Test `resolve_model_config` resolution priority chain (override → global)
- Test `get_llm` returns correct `BaseChatModel` subclass per provider
- Mock actual LLM API calls — no live API calls in unit tests

---

### Verification (Phase 2)

```bash
pytest tests/unit/test_llm_router.py -v
python -c "
from pm_agent.config.loader import load_config
from pm_agent.adapters.llm.factory import get_llm
cfg = load_config()
llm = get_llm(cfg.llm.fast)
resp = llm.invoke('Say hello in one word.')
print(resp.content)
"
```

**Exit condition**: `get_llm` returns correct model per tier; live smoke test gets a response from at least one provider.

---

## Phase 3 — Context Management Layer

**Goal**: Every LLM call in the system is automatically guarded against context overflow. LangGraph state is trimmed when it bloats. Ritual outcomes persist to SQLite across sessions.

**Entry condition**: Phase 2 complete.

**This is the most critical phase to get right** — it sits underneath every subsequent phase. Build it carefully, test it exhaustively.

---

### Task 3.1 — Model context limits registry

**File**: `pm_agent/context/limits.py`

```python
MODEL_CONTEXT_LIMITS: dict[str, int] = {
    # Gemini
    "models/gemini-2.0-flash": 1_048_576,
    "models/gemini-2.5-pro": 1_048_576,
    # Claude
    "claude-sonnet-4-20250514": 200_000,
    "claude-opus-4-20250514": 200_000,
    # Azure OpenAI
    "gpt-4o": 128_000,
    # Ollama — common models at default num_ctx
    # Override via ollama_context_limit in config if you've set a custom num_ctx
    "llama3.2": 131_072,
    "llama3.1": 131_072,
    "mistral": 32_768,
    "mistral-nemo": 131_072,
    "qwen2.5-coder": 131_072,
    "qwen2.5": 131_072,
    "deepseek-r1": 131_072,
    "phi4": 16_384,
    "gemma2": 8_192,
}

def get_context_limit(model_config: ModelTierConfig) -> int:
    # Ollama: prefer explicit config override (matches your actual num_ctx)
    if model_config.provider == "ollama" and model_config.ollama_context_limit:
        return model_config.ollama_context_limit
    limit = MODEL_CONTEXT_LIMITS.get(model_config.model)
    if not limit:
        # safe fallback — treat unknown models conservatively
        fallback = 8_192 if model_config.provider == "ollama" else 128_000
        return fallback
    return limit
```

> **Note**: The function signature changed from `get_context_limit(model_name: str)` to `get_context_limit(model_config: ModelTierConfig)` to support the Ollama override. Update all call sites in `ContextBudgetWatcher` accordingly.

---

### Task 3.2 — `ContextBudgetWatcher`

**File**: `pm_agent/context/budget_watcher.py`

Two-stage implementation as specced:

```python
class BudgetStatus(BaseModel):
    estimated_pct: float
    actual_pct: Optional[float] = None
    threshold: float
    should_compress: bool
    model_limit_tokens: int

class ContextBudgetWatcher:
    def check(
        self,
        messages: list[BaseMessage],
        model_config: ModelTierConfig,
        ritual_name: str,
        ritual_overrides: dict,
    ) -> BudgetStatus:
        limit = get_context_limit(model_config.model)
        threshold = self._get_threshold(ritual_name, ritual_overrides)

        # Stage 1: character proxy (always runs, zero cost)
        total_chars = sum(len(str(m.content)) for m in messages)
        estimated_tokens = total_chars / 4
        estimated_pct = estimated_tokens / limit

        if estimated_pct < 0.75:
            return BudgetStatus(
                estimated_pct=estimated_pct,
                threshold=threshold,
                should_compress=False,
                model_limit_tokens=limit,
            )

        # Stage 2: actual token count via provider API
        actual_tokens = self._count_tokens_via_api(messages, model_config)
        actual_pct = actual_tokens / limit

        return BudgetStatus(
            estimated_pct=estimated_pct,
            actual_pct=actual_pct,
            threshold=threshold,
            should_compress=actual_pct >= threshold,
            model_limit_tokens=limit,
        )
```

> **LangChain note**: Use `llm.get_num_tokens_from_messages(messages)` for the Stage 2 count — it's available on `ChatGoogleGenerativeAI`, `ChatAnthropic`, and `AzureChatOpenAI`. Falls back to `tiktoken` for OpenAI-compatible models.

---

### Task 3.3 — `SummarizationMiddleware`

**File**: `pm_agent/context/summarization.py`

```python
SUMMARIZATION_PROMPT = """You are a context compressor for a project management agent.
Summarize the following conversation history concisely, preserving:
- All decisions made
- All ticket IDs referenced and their current status
- All ritual outputs produced
- Any blockers or open questions raised
- Team member assignments mentioned

Be factual and terse. Output only the summary, no preamble.

Prior summary (if any):
{prior_summary}

Messages to compress:
{messages_to_compress}
"""

class CompressionResult(BaseModel):
    compressed_messages: list[BaseMessage]
    rolling_summary: str
    tokens_before: int
    tokens_after: int
    compression_ratio: float

class SummarizationMiddleware:
    def __init__(self, fast_llm: BaseChatModel, tail_window: int = 4):
        self.llm = fast_llm
        self.tail_window = tail_window

    async def compress(
        self,
        messages: list[BaseMessage],
        prior_summary: Optional[str],
        model_config: ModelTierConfig,
    ) -> CompressionResult:
        # always preserve system message + tail
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        tail = messages[-self.tail_window:]
        to_compress = [m for m in messages
                       if m not in system_msgs and m not in tail]

        if not to_compress:
            # nothing to compress — tail is all we have
            return CompressionResult(
                compressed_messages=messages,
                rolling_summary=prior_summary or "",
                tokens_before=0, tokens_after=0, compression_ratio=1.0
            )

        prompt = SUMMARIZATION_PROMPT.format(
            prior_summary=prior_summary or "None",
            messages_to_compress="\n".join(
                f"[{m.__class__.__name__}]: {m.content}" for m in to_compress
            )
        )
        summary_response = await self.llm.ainvoke(prompt)
        new_summary = summary_response.content

        compressed = system_msgs + [HumanMessage(content=f"[CONTEXT SUMMARY]\n{new_summary}")] + tail

        return CompressionResult(
            compressed_messages=compressed,
            rolling_summary=new_summary,
            tokens_before=len(to_compress),
            tokens_after=1,   # replaced with 1 summary message
            compression_ratio=1 / max(len(to_compress), 1),
        )
```

---

### Task 3.4 — `StateCompressor` (LangGraph node)

**File**: `pm_agent/context/state_compressor.py`

Implemented as a function that takes and returns `PMAgentState` — plugs directly into LangGraph as a node:

```python
def compress_state(state: PMAgentState) -> PMAgentState:
    """LangGraph pass-through node. Trims state fields when thresholds exceeded."""
    cfg = load_config().context_management.state_compressor
    updated = state.model_copy()

    if len(state.tickets) > cfg.max_tickets_in_state:
        updated.tickets = [
            TicketSummary(
                id=t.id, title=t.title,
                status=t.status, priority=t.priority
            ) for t in state.tickets
        ]
        updated.state_compressed = True

    if len(state.execution_trace) > cfg.max_trace_entries:
        tail = state.execution_trace[-cfg.trace_keep_last:]
        summary = f"[TRACE COMPRESSED: {len(state.execution_trace) - cfg.trace_keep_last} entries omitted]"
        updated.execution_trace = [summary] + tail
        updated.state_compressed = True

    return updated
```

> **LangGraph note**: Add this node between `execute_ritual` and `evaluate_autonomy` in the graph definition. Because LangGraph nodes must return either state updates or the full state, return the full updated state dict.

---

### Task 3.5 — `AgentMemoryStore`

**File**: `pm_agent/context/memory/base.py` and `pm_agent/context/memory/sqlite.py`

```python
class RitualMemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ritual_name: str
    sdlc_mode: str
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    trigger: Literal["cron", "prompt"]
    outcome_summary: str
    tickets_affected: list[str] = []
    decisions: list[str] = []
    model_used: str
    compression_occurred: bool = False

class AgentMemoryStore(ABC):
    @abstractmethod
    async def write(self, entry: RitualMemoryEntry) -> None: ...

    @abstractmethod
    async def get_recent(self, ritual_name: str, limit: int = 5) -> list[RitualMemoryEntry]: ...

    @abstractmethod
    async def get_context_injection(self, ritual_name: str) -> str: ...
```

**SQLite backend** (`sqlite.py`): Single `ritual_memory` table. Schema:

```sql
CREATE TABLE IF NOT EXISTS ritual_memory (
    id TEXT PRIMARY KEY,
    ritual_name TEXT NOT NULL,
    sdlc_mode TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    trigger TEXT NOT NULL,
    outcome_summary TEXT NOT NULL,
    tickets_affected TEXT NOT NULL,  -- JSON array
    decisions TEXT NOT NULL,          -- JSON array
    model_used TEXT NOT NULL,
    compression_occurred INTEGER NOT NULL
);
CREATE INDEX idx_ritual_name ON ritual_memory(ritual_name, executed_at DESC);
```

`get_context_injection` returns a formatted string like:

```
RECENT RITUAL HISTORY (last 3 standup_agenda runs):
- 2026-05-01 08:45 [cron]: Standup agenda generated. Tickets #12, #15 flagged blocked. Decision: #15 escalated.
- 2026-04-30 08:45 [cron]: #8 closed. #19 added to agenda.
- 2026-04-29 08:45 [cron]: No blockers. Sprint on track.
```

---

### Task 3.6 — `ContextAwareLLMInvoker`

**File**: `pm_agent/context/invoker.py`

The single enforcement seam — all ritual code calls this:

```python
class ContextAwareLLMInvoker:
    def __init__(
        self,
        watcher: ContextBudgetWatcher,
        summarizer: SummarizationMiddleware,
        fast_llm: BaseChatModel,
    ):
        self.watcher = watcher
        self.summarizer = summarizer

    async def invoke(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        model_config: ModelTierConfig,
        ritual_name: str,
        state: PMAgentState,
        ritual_overrides: dict = {},
    ) -> tuple[BaseMessage, PMAgentState]:
        """
        Invoke the LLM with automatic context compression if needed.
        Returns (response, updated_state).
        """
        budget = self.watcher.check(messages, model_config, ritual_name, ritual_overrides)

        if budget.should_compress:
            log.info("context_compression_triggered",
                     ritual=ritual_name,
                     pct=budget.actual_pct,
                     threshold=budget.threshold)
            result = await self.summarizer.compress(
                messages, state.rolling_summary, model_config
            )
            messages = result.compressed_messages
            state = state.model_copy(update={
                "rolling_summary": result.rolling_summary,
                "context_budget_used_pct": budget.actual_pct or budget.estimated_pct,
            })

        response = await llm.ainvoke(messages)
        return response, state
```

---

### Task 3.7 — Unit tests (comprehensive)

**Files**: `tests/unit/test_budget_watcher.py`, `tests/unit/test_summarization.py`, `tests/unit/test_state_compressor.py`, `tests/unit/test_agent_memory.py`

Critical test cases:
- `BudgetWatcher`: proxy exits early below 75%; Stage 2 fires between 75-85%; compression triggered at 85%+
- `BudgetWatcher`: threshold override respected per ritual
- `SummarizationMiddleware`: system message always preserved; tail always preserved; rolling summary accumulates across two compressions
- `SummarizationMiddleware`: handles edge case where messages list is shorter than tail_window
- `StateCompressor`: tickets compressed to `TicketSummary` at threshold; trace trimmed; `state_compressed` flag set
- `AgentMemoryStore`: write + read round-trip; `get_context_injection` format matches expected string; entries returned in descending order

---

### Verification (Phase 3)

```bash
pytest tests/unit/test_budget_watcher.py tests/unit/test_summarization.py \
       tests/unit/test_state_compressor.py tests/unit/test_agent_memory.py -v
```

**Exit condition**: All context management unit tests pass. `ContextAwareLLMInvoker` invokable in isolation with a mocked LLM.

---

## Phase 4 — Skill System

**Goal**: A `skills/` folder with front matter `skill.md` files can be scanned at startup, injected into the LLM system prompt as a compact index, and lazy-loaded + invoked via MCP when the LLM selects a skill.

**Entry condition**: Phase 2 complete (LLM router available for skill execution).

---

### Task 4.1 — `skill.md` schema

**File**: `pm_agent/skills/models.py`

```python
class SkillPhase(StrEnum):
    ENRICH = "enrich"
    EXECUTE = "execute"
    BOTH = "both"

class SkillSummary(BaseModel):
    """Front matter only — loaded at startup."""
    name: str
    description: str
    triggers: list[str]
    mcp_server: str
    phase: SkillPhase
    input_schema: dict[str, str]

class SkillDefinition(SkillSummary):
    """Full definition — lazy loaded on demand."""
    full_content: str   # everything below the --- separator
```

---

### Task 4.2 — `SkillRegistry`

**File**: `pm_agent/skills/registry.py`

```python
class SkillRegistry:
    def __init__(self, skills_folder: Path):
        self._folder = skills_folder
        self._index: dict[str, SkillSummary] = {}
        self._cache: dict[str, SkillDefinition] = {}

    def load_index(self) -> list[SkillSummary]:
        """Scan skills/*/skill.md, parse front matter only."""
        for skill_dir in self._folder.iterdir():
            skill_file = skill_dir / "skill.md"
            if not skill_file.exists():
                continue
            front_matter = self._parse_front_matter(skill_file)
            summary = SkillSummary.model_validate(front_matter)
            self._index[summary.name] = summary
        return list(self._index.values())

    def get_system_prompt_injection(self) -> str:
        lines = ["AVAILABLE SKILLS:"]
        for s in self._index.values():
            triggers = ", ".join(f'"{t}"' for t in s.triggers[:2])
            lines.append(f"- {s.name}: {s.description}. Use when: {triggers}")
        return "\n".join(lines)

    def load(self, skill_name: str) -> SkillDefinition:
        """Lazy full load — only reads full file on first access."""
        if skill_name in self._cache:
            return self._cache[skill_name]
        skill_file = self._folder / skill_name / "skill.md"
        full = skill_file.read_text()
        parts = full.split("---", 2)
        front = yaml.safe_load(parts[1])
        defn = SkillDefinition(**front, full_content=parts[2] if len(parts) > 2 else "")
        self._cache[skill_name] = defn
        return defn

    def _parse_front_matter(self, path: Path) -> dict:
        content = path.read_text()
        parts = content.split("---", 2)
        return yaml.safe_load(parts[1]) if len(parts) >= 2 else {}
```

---

### Task 4.3 — `SkillExecutor`

**File**: `pm_agent/skills/executor.py`

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

class SkillResult(BaseModel):
    skill_name: str
    phase: SkillPhase
    output: dict
    success: bool
    error: Optional[str] = None

class SkillExecutor:
    def __init__(self, registry: SkillRegistry, llm: BaseChatModel):
        self.registry = registry
        self.llm = llm

    async def invoke(self, skill_name: str, inputs: dict) -> SkillResult:
        defn = self.registry.load(skill_name)
        try:
            async with MultiServerMCPClient({
                skill_name: {"url": defn.mcp_server, "transport": "sse"}
            }) as client:
                tools = client.get_tools()
                agent = create_react_agent(self.llm, tools)
                result = await agent.ainvoke({
                    "messages": [HumanMessage(content=str(inputs))]
                })
                return SkillResult(
                    skill_name=skill_name,
                    phase=defn.phase,
                    output={"response": result["messages"][-1].content},
                    success=True,
                )
        except Exception as e:
            return SkillResult(
                skill_name=skill_name, phase=defn.phase,
                output={}, success=False, error=str(e)
            )
```

> **LangChain note**: `MultiServerMCPClient` from `langchain-mcp-adapters` handles SSE MCP connections. Use `create_react_agent` from `langgraph.prebuilt` to let the LLM drive tool selection within a skill invocation.

---

### Task 4.4 — Seed skill files

Create `skill.md` files for the two initial execute-phase skills:

**`skills/github_create_issue/skill.md`**:
```markdown
---
name: github_create_issue
description: Creates a GitHub issue with title, body, labels, and optional assignee.
triggers:
  - "create github issue"
  - "write ticket to github"
  - "commit task to github"
mcp_server: https://mcp.github.com/sse
phase: execute
input_schema:
  repo: str
  title: str
  body: str
  labels: "List[str]"
  assignee: "Optional[str]"
---

## Usage Notes
Use this skill when the approved HITL queue tasks need to be committed to GitHub Issues.
Pass the full ticket body as markdown. Labels should follow the project label convention.
```

Create similar file for `jira_create_ticket`.

---

### Task 4.5 — Unit tests

**File**: `tests/unit/test_skill_registry.py`

- Test `load_index` scans correctly, returns `SkillSummary` objects
- Test `get_system_prompt_injection` format
- Test `load` caches on second access (no file re-read)
- Test `SkillExecutor.invoke` with mocked MCP server (mock `MultiServerMCPClient`)
- Test graceful failure when MCP server unavailable returns `SkillResult(success=False)`

---

### Verification (Phase 4)

```bash
pytest tests/unit/test_skill_registry.py -v
python -c "
from pm_agent.skills.registry import SkillRegistry
from pathlib import Path
r = SkillRegistry(Path('skills'))
r.load_index()
print(r.get_system_prompt_injection())
"
```

**Exit condition**: Registry scans and injects correctly; executor handles MCP failure gracefully.

---

## Phase 5 — HITL Task Queue

**Goal**: Generated task drafts can be pushed to a queue, reviewed item-by-item via CLI (edit/approve/delete/add), and the approved batch retrieved for downstream commit.

**Entry condition**: Phase 0 complete (data models available).

---

### Task 5.1 — Queue data models

**File**: `pm_agent/adapters/queue/models.py`

```python
class QueueStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    DELETED = "deleted"

class TaskDraft(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    labels: list[str] = []
    suggested_assignee: Optional[str] = None
    source_reference: str = ""       # e.g. "BRD section 3.2"
    queue_status: QueueStatus = QueueStatus.PENDING
    edited_fields: Optional[dict] = None

class QueueSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    items: list[TaskDraft] = []
    status: Literal["open", "complete"] = "open"
    target_source: Literal["github", "jira"] = "github"
    expires_at: Optional[datetime] = None
```

---

### Task 5.2 — `HITLQueue` ABC

**File**: `pm_agent/adapters/queue/base.py`

```python
class HITLQueue(ABC):
    @abstractmethod
    async def push(self, drafts: list[TaskDraft], target: str) -> QueueSession: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> QueueSession: ...

    @abstractmethod
    async def approve_item(self, session_id: str, draft_id: str) -> None: ...

    @abstractmethod
    async def edit_item(self, session_id: str, draft_id: str, fields: dict) -> None: ...

    @abstractmethod
    async def delete_item(self, session_id: str, draft_id: str) -> None: ...

    @abstractmethod
    async def add_item(self, session_id: str, draft: TaskDraft) -> None: ...

    @abstractmethod
    async def get_approved(self, session_id: str) -> list[TaskDraft]: ...

    @abstractmethod
    async def list_open_sessions(self) -> list[QueueSession]: ...
```

---

### Task 5.3 — `InProcessQueueBackend`

**File**: `pm_agent/adapters/queue/in_process.py`

Dict-backed implementation. Stores `QueueSession` objects in memory. TTL enforced on `get_session` (raises `SessionExpiredError` if past `expires_at`). Sufficient for single-process, single-user v0.3.

---

### Task 5.4 — `SQLiteQueueBackend`

**File**: `pm_agent/adapters/queue/sqlite.py`

Persists `QueueSession` as JSON blobs in a single `queue_sessions` table. Uses `aiosqlite` for async I/O. Sessions survive process restarts. Schema:

```sql
CREATE TABLE IF NOT EXISTS queue_sessions (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,           -- JSON-serialized QueueSession
    created_at TEXT NOT NULL,
    expires_at TEXT,
    status TEXT NOT NULL
);
```

---

### Task 5.5 — CLI triage interface

**File**: `pm_agent/cli/queue.py`

```python
import typer
from rich.console import Console
from rich.panel import Panel

queue_app = typer.Typer()
console = Console()

@queue_app.command("review")
def review_queue(session_id: str):
    """Interactive per-item triage of a HITL queue session."""
    session = asyncio.run(get_queue().get_session(session_id))
    pending = [i for i in session.items if i.queue_status == QueueStatus.PENDING]

    for idx, item in enumerate(pending, 1):
        console.print(Panel(
            f"[bold]{item.title}[/bold]\n"
            f"Priority: {item.priority} | Labels: {', '.join(item.labels)}\n"
            f"Source: {item.source_reference}\n\n"
            f"{item.description[:200]}...",
            title=f"[{idx}/{len(pending)}]"
        ))
        action = typer.prompt("(a)pprove  (e)dit  (d)elete  (s)kip", default="a")
        # handle each action...

    approved = asyncio.run(get_queue().get_approved(session_id))
    if typer.confirm(f"\n{len(approved)} approved. Commit to {session.target_source}?"):
        # trigger batch commit
        ...
```

---

### Task 5.6 — Unit tests

**File**: `tests/unit/test_hitl_queue.py`

- Test `push` creates session with correct item count
- Test `approve_item` / `edit_item` / `delete_item` update `queue_status`
- Test `add_item` adds a new draft to an open session
- Test `get_approved` returns only approved + edited items (not deleted)
- Test `SQLiteQueueBackend` persistence: push, restart process, session still retrievable
- Test TTL expiry raises `SessionExpiredError`

---

### Verification (Phase 5)

```bash
pytest tests/unit/test_hitl_queue.py -v
# manual smoke test
python -c "
import asyncio
from pm_agent.adapters.queue.in_process import InProcessQueueBackend
from pm_agent.adapters.queue.models import TaskDraft
q = InProcessQueueBackend()
draft = TaskDraft(title='Test task', description='desc', priority='high')
session = asyncio.run(q.push([draft], 'github'))
print('Session:', session.id)
asyncio.run(q.approve_item(session.id, draft.id))
approved = asyncio.run(q.get_approved(session.id))
print('Approved:', len(approved))
"
```

**Exit condition**: Both backends pass all unit tests; CLI `review` command renders a queue session interactively.

---

## Phase 6 — `task_creator` Ritual

**Goal**: `pm-agent run task_creator --input path/to/brd.md` parses the document, generates task drafts, routes them through the HITL queue CLI, and commits approved tasks to GitHub/Jira via the Skill System.

**Entry condition**: Phases 1, 2, 3, 4, 5 all complete.

---

### Task 6.1 — BRD parser

**File**: `pm_agent/skills/parsers/brd.py`

```python
class BRDParser:
    """Extracts candidate tasks from a BRD document (PDF, DOCX, or MD)."""

    async def parse(self, path: Path) -> str:
        """Returns raw extracted text."""
        match path.suffix.lower():
            case ".pdf":  return self._parse_pdf(path)
            case ".docx": return self._parse_docx(path)
            case ".md":   return path.read_text()
            case _: raise ValueError(f"Unsupported BRD format: {path.suffix}")

    def _parse_pdf(self, path: Path) -> str:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join(page.extract_text() for page in reader.pages)

    def _parse_docx(self, path: Path) -> str:
        from docx import Document
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
```

---

### Task 6.2 — Task list parser

**File**: `pm_agent/skills/parsers/task_list.py`

Handles plain text or markdown lists. Splits on newlines, strips list markers (`-`, `*`, `1.`), returns `List[str]` of candidate task titles. Minimal processing — let the LLM do the heavy lifting in the next step.

---

### Task 6.3 — `task_creator` LangGraph subgraph

**File**: `pm_agent/rituals/task_creator.py`

Nodes in order:

```
parse_input
    │  (BRDParser or TaskListParser → raw text)
    ▼
enrich_context
    │  (SkillRegistry identifies enrich-phase skills from system prompt;
    │   invoke them via SkillExecutor; inject results into prompt)
    ▼
generate_task_drafts          ← ContextAwareLLMInvoker.invoke() used here
    │  (mid-tier LLM with structured output → List[TaskDraft])
    │  (enforces max_tasks_per_session from config)
    ▼
push_to_hitl_queue
    │  (HITLQueue.push() → QueueSession)
    │  state.hitl_queue_id = session.id
    ▼
await_queue_drain             ← interrupt node: pauses graph
    │  (APScheduler or CLI triggers resume after user completes review)
    ▼
batch_commit                  ← SkillExecutor.invoke(execute-phase skill)
    │  (for each approved draft: call github_create_issue or jira_create_ticket)
    ▼
emit_output
    │  (log results, write RitualMemoryEntry to AgentMemoryStore)
    ▼
trigger_task_prioritization   ← conditional: auto_trigger_prioritization=true
```

> **LangGraph note**: Use `interrupt()` from `langgraph.types` at `await_queue_drain` to pause the graph and hand control back to the user. Resume with `graph.invoke(None, config)` after the queue review completes. This is the correct pattern for long-running human-in-the-loop workflows in LangGraph v0.2+.

**Structured output schema for `generate_task_drafts`**:
```python
class TaskDraftList(BaseModel):
    drafts: list[TaskDraft]
    total_count: int
    source_document: str

llm_with_output = get_structured_llm(mid_llm, TaskDraftList)
```

---

### Task 6.4 — Integration test

**File**: `tests/integration/test_task_creator.py`

Use `tests/fixtures/sample_brd.md` — a minimal 2-page fake BRD with 5-8 extractable requirements. Assert:
- Parser extracts text without error
- LLM generates between 1 and 30 `TaskDraft` objects
- HITL queue session created with correct item count
- After simulated approval, `SkillExecutor` is called with correct inputs (mock the MCP call)

---

### Verification (Phase 6)

```bash
pm-agent run task_creator --input tests/fixtures/sample_brd.md --dry-run
# should print generated drafts, not commit anything
```

**Exit condition**: End-to-end `task_creator` runs against a sample BRD, generates drafts, shows HITL queue CLI, and on approval calls the skill executor (mocked for dry-run).

---

## Phase 7 — SDD Mode + Core Rituals + Agent Core Graph

**Goal**: The full LangGraph agent core is wired with all three autonomy paths. `standup_agenda` runs end-to-end autonomously. `spec_creation` runs with approval gate. `SDDMode` shapes both.

**Entry condition**: Phases 1, 2, 3 complete.

---

### Task 7.1 — `PMAgentState`

**File**: `pm_agent/core/state.py`

```python
from langgraph.graph import MessagesState
from typing import Annotated
import operator

class PMAgentState(TypedDict):
    ritual_name: str
    sdlc_mode: str
    tickets: Annotated[list, operator.add]    # LangGraph reducer: append-only
    team: list[TeamMember]
    llm_output: Optional[Any]
    approval_status: Optional[str]
    hitl_queue_id: Optional[str]
    messages: Annotated[list[BaseMessage], operator.add]
    rolling_summary: Optional[str]
    context_budget_used_pct: float
    state_compressed: bool
    execution_trace: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
    trigger: Literal["cron", "prompt"]
```

> **LangGraph note**: Use `Annotated[list, operator.add]` for list fields that accumulate across nodes (tickets, trace, errors, messages). This tells LangGraph to append rather than overwrite when nodes return partial state updates.

---

### Task 7.2 — SDLC Mode layer

**File**: `pm_agent/sdlc/base.py` and `pm_agent/sdlc/sdd.py`

```python
class SDLCMode(ABC):
    name: str

    @abstractmethod
    def get_ritual(self, name: str) -> RitualDefinition: ...

    @abstractmethod
    def get_context_prompt(self) -> str: ...
```

`SDDMode.get_context_prompt()` returns:

```
You are a project management agent operating in Spec-Driven Development (SDD) mode.
In SDD mode:
- Every task should have an associated spec before implementation begins.
- Prioritize spec_creation and spec_review tasks.
- Tasks without approved specs are deprioritized unless they ARE spec tasks.
- Reference spec sections when creating standup agenda items.
- Spec authorship influences delegation decisions.
```

---

### Task 7.3 — Top-level LangGraph graph

**File**: `pm_agent/core/agent.py`

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

def build_agent_graph(checkpointer=None) -> CompiledGraph:
    graph = StateGraph(PMAgentState)

    graph.add_node("load_context", load_context_node)
    graph.add_node("execute_ritual", execute_ritual_node)
    graph.add_node("compress_state", compress_state)          # Phase 3
    graph.add_node("evaluate_autonomy", evaluate_autonomy_node)
    graph.add_node("commit_action", commit_action_node)
    graph.add_node("post_for_approval", post_for_approval_node)
    graph.add_node("await_confirmation", await_confirmation_node)
    graph.add_node("push_to_hitl_queue", push_to_hitl_queue_node)
    graph.add_node("await_queue_drain", await_queue_drain_node)
    graph.add_node("batch_commit", batch_commit_node)
    graph.add_node("emit_output", emit_output_node)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "execute_ritual")
    graph.add_edge("execute_ritual", "compress_state")
    graph.add_edge("compress_state", "evaluate_autonomy")

    graph.add_conditional_edges("evaluate_autonomy", route_by_autonomy, {
        "autonomous":        "commit_action",
        "approval_required": "post_for_approval",
        "hitl_queue":        "push_to_hitl_queue",
    })

    graph.add_edge("commit_action", "emit_output")
    graph.add_edge("post_for_approval", "await_confirmation")
    graph.add_conditional_edges("await_confirmation", route_by_approval, {
        "confirmed": "commit_action",
        "rejected":  "emit_output",
    })
    graph.add_edge("push_to_hitl_queue", "await_queue_drain")
    graph.add_edge("await_queue_drain", "batch_commit")
    graph.add_edge("batch_commit", "emit_output")
    graph.add_edge("emit_output", END)

    return graph.compile(checkpointer=checkpointer)
```

Use `AsyncSqliteSaver` as the checkpointer — this gives you free graph state persistence and resumability (critical for the `await_queue_drain` interrupt).

---

### Task 7.4 — `standup_agenda` ritual node

**File**: `pm_agent/rituals/standup_agenda.py`

```python
STANDUP_PROMPT = """
{sdlc_context}
{memory_context}

You are generating the standup agenda for today.

Open tickets (last 24h activity):
{tickets}

Generate a structured standup agenda with:
1. Blocked items (need immediate attention)
2. In-progress items to discuss
3. Items completing today
4. Upcoming deadlines this week

Group items by spec status in SDD mode.
"""

class StandupAgendaOutput(BaseModel):
    blocked: list[AgendaItem]
    in_progress: list[AgendaItem]
    completing_today: list[AgendaItem]
    upcoming_deadlines: list[AgendaItem]
    generated_at: datetime
```

Call `ContextAwareLLMInvoker.invoke()` — never call `llm.ainvoke()` directly.

---

### Task 7.5 — `spec_creation` ritual node

**File**: `pm_agent/rituals/spec_creation.py`

Largest prompt in the system. Uses strong tier. Output is a full markdown spec document. Approval gate fires before writing anywhere. Post-approval, write the spec to the ticket as a comment (or file — pending OQ-1).

SDD spec template (injected into prompt):
```
## 1. Problem Statement
## 2. Goals
## 3. Non-Goals
## 4. Interface / API
## 5. Data Models
## 6. Test Criteria
## 7. Open Questions
```

---

### Task 7.6 — `emit_output` node (writes to AgentMemoryStore)

**File**: `pm_agent/core/nodes.py`

`emit_output` is always the final node. It:
1. Logs the ritual output to stdout (via `NotificationAdapter`)
2. Generates a brief outcome summary (fast LLM, 2-3 sentences)
3. Writes a `RitualMemoryEntry` to `AgentMemoryStore`

---

### Verification (Phase 7)

```bash
pm-agent run standup_agenda
# should print agenda to stdout, write to memory store

pm-agent run spec_creation --ticket-id 42
# should generate spec draft, prompt for approval, then write to ticket

pytest tests/integration/ -v
```

**Exit condition**: Full agent graph executes both autonomy paths end-to-end. Memory store has entries after each run. `pm-agent memory inspect` shows last 5 entries.

---

## Phase 8 — Remaining Rituals

**Goal**: All 5 remaining rituals implemented and wired into the agent graph. System is feature-complete for SDD mode.

**Entry condition**: Phase 7 complete (agent graph, SDLC layer, and core rituals working).

Each ritual follows the same implementation pattern established in Phase 7: prompt template → structured output schema → `ContextAwareLLMInvoker.invoke()` → autonomy routing.

---

### Task 8.1 — `task_prioritization`

**File**: `pm_agent/rituals/task_prioritization.py`

- **Input**: All open tickets + their labels, ages, assignees, spec status
- **Output**: `PrioritizedTicketList(tickets: list[PrioritizedTicket])` where `PrioritizedTicket` adds `rank: int` and `reasoning: str`
- **SDD behavior**: Penalize tickets with `spec_status: missing`; boost tickets tagged `spec_creation` or `spec_review`
- **Autonomy**: Autonomous — writes priority order to stdout; does not modify ticket source

---

### Task 8.2 — `task_delegation`

**File**: `pm_agent/rituals/task_delegation.py`

- **Input**: Unassigned tickets + team member profiles from config
- **Output**: `DelegationProposal(assignments: list[Assignment])` where `Assignment` has `ticket_id`, `assignee`, `reasoning`
- **SDD behavior**: Spec author gets first consideration for implementation tasks on their own spec
- **Autonomy**: Approval required — proposes assignments, human confirms before any ticket update

---

### Task 8.3 — `reminder_dispatch`

**File**: `pm_agent/rituals/reminder_dispatch.py`

- **Input**: Tickets with `updated_at` older than `stale_threshold_hours` config value
- **Output**: `ReminderBatch(reminders: list[Reminder])` — one reminder per assignee, grouped
- **Autonomy**: Autonomous — sends via `NotificationAdapter`
- **Note**: In v0.3 this prints to stdout. Email/Slack are future adapter implementations.

---

### Task 8.4 — `task_decomposition`

**File**: `pm_agent/rituals/task_decomposition.py`

- **Input**: A single large/vague ticket ID + its spec (if exists)
- **Output**: `DecompositionResult(sub_tickets: list[TicketSpec], spec_stubs: list[str])`
- **SDD behavior**: Each sub-ticket gets a spec stub generated alongside it
- **Autonomy**: Approval required — human reviews the decomposition before sub-tickets are created
- **Post-approval**: Creates sub-tickets via `TicketSourceAdapter.create_ticket()`

---

### Task 8.5 — `spec_review`

**File**: `pm_agent/rituals/spec_review.py`

- **Input**: A spec document (markdown text, from ticket comment or file)
- **Output**: `SpecReview(score: int, gaps: list[str], suggestions: list[str], approved: bool)`
- **Scoring rubric** (injected into prompt): completeness of 7 sections, clarity of interface definition, presence of test criteria, no open questions left unresolved
- **Autonomy**: Approval required — review is posted as a ticket comment after human confirms

---

### Verification (Phase 8)

```bash
pm-agent run task_prioritization
pm-agent run task_delegation
pm-agent run reminder_dispatch
pm-agent run task_decomposition --ticket-id 42
pm-agent run spec_review --ticket-id 42
```

Each command should run end-to-end without error. Check memory store has entries for each.

**Exit condition**: All 8 rituals implemented and runnable. SDD mode is fully operational.

---

## Phase 9 — Scheduler

**Goal**: `standup_agenda` fires automatically at 8:45am on weekdays. Any ritual can be scheduled via `ritual_config.yaml`. Scheduler is startable as a background process.

**Entry condition**: Phase 7 complete (`standup_agenda` runs reliably on demand).

---

### Task 9.1 — `SchedulerAdapter` ABC

**File**: `pm_agent/adapters/scheduler/base.py`

```python
class SchedulerAdapter(ABC):
    @abstractmethod
    def register(self, ritual_name: str, cron: str, kwargs: dict) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def shutdown(self) -> None: ...
```

---

### Task 9.2 — `APSchedulerAdapter`

**File**: `pm_agent/adapters/scheduler/apscheduler.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class APSchedulerAdapter(SchedulerAdapter):
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=load_config().scheduler.timezone)

    def register(self, ritual_name: str, cron: str, kwargs: dict = {}) -> None:
        trigger = CronTrigger.from_crontab(cron)
        self.scheduler.add_job(
            func=run_ritual_async,
            trigger=trigger,
            args=[ritual_name],
            kwargs=kwargs,
            id=ritual_name,
            replace_existing=True,
        )

    def start(self) -> None:
        self._load_from_ritual_config()
        self.scheduler.start()

    def _load_from_ritual_config(self):
        overrides = load_ritual_config()
        for ritual_name, cfg in overrides.items():
            if schedule := cfg.get("schedule"):
                self.register(ritual_name, schedule)
```

`run_ritual_async` is a thin wrapper that builds `PMAgentState` and invokes the compiled graph with `trigger="cron"`.

---

### Task 9.3 — `pm-agent schedule start` command

```bash
pm-agent schedule start
# Runs scheduler in foreground. Ctrl+C to stop.
# Shows registered jobs on startup via rich table.
```

---

### Verification (Phase 9)

Set `standup_agenda` schedule to `"* * * * *"` (every minute) in `ritual_config.yaml`, run `pm-agent schedule start`, confirm it fires within 60 seconds, check memory store for the new entry.

**Exit condition**: Scheduler starts, registers jobs from config, fires rituals on schedule.

---

## Phase 10 — CLI & API Surface

**Goal**: A complete, well-documented CLI with all subcommands. System is operable entirely from the terminal. FastAPI wrapper is stubbed and documented.

**Entry condition**: Phases 7, 8, 9 complete.

---

### Task 10.1 — Full `typer` CLI

**File**: `pm_agent/cli/main.py`

```
pm-agent run <ritual_name> [options]
  --input PATH          (for task_creator)
  --ticket-id STR       (for spec_creation, task_decomposition, spec_review)
  --dry-run             (prints output, no writes)

pm-agent schedule start
pm-agent schedule list

pm-agent queue list
pm-agent queue review <session_id>

pm-agent config validate
pm-agent config show

pm-agent memory inspect [--ritual <name>] [--limit 10]
pm-agent memory prune [--older-than-days 90]

pm-agent skills list
pm-agent skills validate
```

Use `rich` for all table/panel output. Use `typer.echo` for simple text.

---

### Task 10.2 — `FastAPI` stub

**File**: `pm_agent/api/main.py`

Thin wrapper — each endpoint calls the same ritual runner used by the CLI:

```
POST /rituals/{ritual_name}/run
GET  /queue/sessions
GET  /queue/sessions/{session_id}
POST /queue/sessions/{session_id}/items/{item_id}/approve
POST /queue/sessions/{session_id}/items/{item_id}/edit
POST /queue/sessions/{session_id}/commit
GET  /memory/entries
```

Not required for v0.3 to be usable, but wire it up as a stub so it's ready when a web UI comes.

---

### Verification (Phase 10)

```bash
pm-agent --help          # all subcommands visible
pm-agent run standup_agenda --dry-run
pm-agent queue list
pm-agent memory inspect
pm-agent skills list
pm-agent config validate
```

**Exit condition**: All CLI commands work end-to-end. `pm-agent --help` is the primary user-facing documentation.

---

## Cross-Cutting Concerns (apply throughout all phases)

### Error handling contract
Every async method that calls an external API must:
1. Wrap with `tenacity.retry` (3 attempts, exponential backoff)
2. Catch the most specific exception available (not bare `Exception`)
3. On final failure, append to `state.errors` and let the graph continue — never crash the agent

### Logging contract
Every node function must emit at minimum:
- Entry log: `log.info("node_start", node=name, ritual=ritual_name)`
- Exit log with key outputs: `log.info("node_complete", node=name, output_summary=...)`
- On error: `log.error("node_error", node=name, error=str(e))`

### Test contract
- Unit tests: no live API calls, all external I/O mocked
- Integration tests: may make live calls, gated by `INTEGRATION_TESTS=1` env var
- Every ritual must have at least one unit test and one integration test

### Type safety
Run `mypy pm_agent/` before every phase exit. Zero type errors required.

---

## Summary Checklist

| Phase | Deliverable | Key LangChain Component |
|---|---|---|
| 0 | Scaffold + config | `pydantic-settings` |
| 1 | Ticket adapters | — (pure data layer) |
| 2 | LLM router | `BaseChatModel`, provider packages |
| 3 | Context management | `AsyncSqliteSaver`, `BaseChatModel.get_num_tokens_from_messages` |
| 4 | Skill system | `langchain-mcp-adapters`, `create_react_agent` |
| 5 | HITL queue | `aiosqlite` |
| 6 | `task_creator` | `langgraph.types.interrupt`, `StateGraph` |
| 7 | SDD + core rituals | `StateGraph`, `with_structured_output`, `AsyncSqliteSaver` |
| 8 | Remaining rituals | `with_structured_output` |
| 9 | Scheduler | `APScheduler`, `AsyncIOScheduler` |
| 10 | CLI + API | `typer`, `FastAPI` |
