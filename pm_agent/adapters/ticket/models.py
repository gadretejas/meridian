from datetime import datetime
from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel


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
