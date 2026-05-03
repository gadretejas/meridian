"""
AgentMemoryStore — abstract base and shared data model.

RitualMemoryEntry records what happened after each ritual run.
Implementations persist these entries (SQLite in production, in-process for tests).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


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
    async def write(self, entry: RitualMemoryEntry) -> None:
        """Persist a ritual memory entry."""
        ...

    @abstractmethod
    async def get_recent(
        self,
        ritual_name: str,
        limit: int = 5,
    ) -> list[RitualMemoryEntry]:
        """Return the most recent entries for a ritual, newest first."""
        ...

    @abstractmethod
    async def get_context_injection(self, ritual_name: str) -> str:
        """
        Return a formatted string of recent ritual history suitable for
        injecting into the system prompt as long-term memory context.
        """
        ...
