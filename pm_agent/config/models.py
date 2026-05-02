"""
Pydantic v2 configuration models for PM Agent.
These are the source of truth for config.yaml deserialization.
"""

from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


class ModelTierConfig(BaseModel):
    """Configuration for a single LLM model tier."""
    provider: Literal["gemini", "claude", "azure_openai", "ollama"]
    model: str
    temperature: float = 0.3
    max_tokens: int = 4096
    base_url: Optional[str] = None  # Ollama: override default http://localhost:11434
    ollama_context_limit: Optional[int] = None  # Ollama: set to match your num_ctx value


class LLMConfig(BaseModel):
    """LLM tier configuration."""
    fast: ModelTierConfig
    mid: ModelTierConfig
    strong: ModelTierConfig


class GitHubConfig(BaseModel):
    """GitHub ticket source configuration."""
    repo: str
    token_env: str = "GITHUB_TOKEN"


class JiraConfig(BaseModel):
    """Jira ticket source configuration."""
    url: str
    email_env: str = "JIRA_EMAIL"
    token_env: str = "JIRA_TOKEN"


class TicketSourcesConfig(BaseModel):
    """Ticket source routing configuration."""
    primary: Literal["github", "jira"]
    github: Optional[GitHubConfig] = None
    jira: Optional[JiraConfig] = None


class StateCompressorConfig(BaseModel):
    """Configuration for state compression thresholds."""
    max_tickets_in_state: int = 50
    max_trace_entries: int = 100
    trace_keep_last: int = 20


class MemoryStoreConfig(BaseModel):
    """Configuration for ritual memory persistence."""
    backend: Literal["in_process", "sqlite"] = "sqlite"
    sqlite_path: str = "~/.pm-agent/memory.db"


class ContextManagementConfig(BaseModel):
    """Context management and budget settings."""
    threshold: float = 0.85  # Compression threshold (85% of max context)
    tail_window: int = 4  # Messages to preserve after compression
    summarizer_model: ModelTierConfig = Field(
        default_factory=lambda: ModelTierConfig(
            provider="gemini",
            model="models/gemini-2.0-flash",
            temperature=0.3,
            max_tokens=1024,
        )
    )
    state_compressor: StateCompressorConfig = Field(default_factory=StateCompressorConfig)
    memory_store: MemoryStoreConfig = Field(default_factory=MemoryStoreConfig)


class HITLQueueConfig(BaseModel):
    """Human-in-the-loop queue configuration."""
    backend: Literal["in_process", "sqlite", "redis"] = "sqlite"
    sqlite_path: str = "~/.pm-agent/queue.db"
    item_ttl_hours: int = 48


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""
    timezone: str = "UTC"
    enable_persistence: bool = True


class ApprovalConfig(BaseModel):
    """Approval gate configuration."""
    approval_timeout_hours: int = 24
    require_approval_for: list[str] = Field(
        default_factory=lambda: ["spec_creation", "task_delegation", "task_decomposition"]
    )


class NotificationsConfig(BaseModel):
    """Notification configuration."""
    enabled: bool = True
    channels: list[Literal["stdout", "email", "slack"]] = ["stdout"]


class TeamMemberConfig(BaseModel):
    """Team member profile in the config."""
    name: str
    handles: dict[str, str] = Field(default_factory=dict)  # {"github": "...", "jira": "..."}
    skills: list[str] = Field(default_factory=list)


class ProjectConfig(BaseModel):
    """Project-level configuration."""
    name: str
    sdlc_mode: Literal["sdd", "agile", "waterfall", "hve"] = "sdd"


class SkillsConfig(BaseModel):
    """Skills system configuration."""
    enabled: bool = True
    auto_discover: bool = True
    folder: str = "skills"


class AppConfig(BaseModel):
    """Complete application configuration."""
    project: ProjectConfig
    ticket_sources: TicketSourcesConfig
    llm: LLMConfig
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    hitl_queue: HITLQueueConfig = Field(default_factory=HITLQueueConfig)
    context_management: ContextManagementConfig = Field(default_factory=ContextManagementConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    team: list[TeamMemberConfig] = Field(default_factory=list)
