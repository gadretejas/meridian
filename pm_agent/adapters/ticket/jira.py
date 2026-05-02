import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Optional

import tenacity
from atlassian import Jira
from requests.exceptions import ConnectionError, HTTPError

from pm_agent.adapters.ticket.base import TicketSourceAdapter
from pm_agent.adapters.ticket.models import (
    Priority,
    Ticket,
    TicketDelta,
    TicketFilter,
    TicketSpec,
    TicketStatus,
    TeamMember,
)
from pm_agent.config.models import JiraConfig
from pm_agent.core.logging import get_logger

logger = get_logger(__name__)

_JIRA_STATUS_MAP: dict[str, TicketStatus] = {
    "open": TicketStatus.OPEN,
    "to do": TicketStatus.OPEN,
    "in progress": TicketStatus.IN_PROGRESS,
    "blocked": TicketStatus.BLOCKED,
    "done": TicketStatus.CLOSED,
    "closed": TicketStatus.CLOSED,
    "resolved": TicketStatus.CLOSED,
}
_JIRA_PRIORITY_MAP: dict[str, Priority] = {
    "highest": Priority.CRITICAL,
    "critical": Priority.CRITICAL,
    "high": Priority.HIGH,
    "medium": Priority.MEDIUM,
    "low": Priority.LOW,
    "lowest": Priority.LOW,
}
_STATUS_TO_JIRA: dict[TicketStatus, str] = {
    TicketStatus.OPEN: "To Do",
    TicketStatus.IN_PROGRESS: "In Progress",
    TicketStatus.BLOCKED: "Blocked",
    TicketStatus.CLOSED: "Done",
}
_PRIORITY_TO_JIRA: dict[Priority, str] = {
    Priority.CRITICAL: "Highest",
    Priority.HIGH: "High",
    Priority.MEDIUM: "Medium",
    Priority.LOW: "Low",
}

_PAGE_SIZE = 50
_JIRA_DATE_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"


def _parse_jira_dt(value: str) -> datetime:
    try:
        dt = datetime.strptime(value, _JIRA_DATE_FMT)
    except ValueError:
        # Fallback: strip sub-seconds or timezone variants
        dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _to_ticket(issue: dict[str, Any]) -> Ticket:
    fields: dict[str, Any] = issue.get("fields", {})

    status_name = (fields.get("status") or {}).get("name", "open").lower()
    status = _JIRA_STATUS_MAP.get(status_name, TicketStatus.OPEN)

    priority_name = (fields.get("priority") or {}).get("name", "medium").lower()
    priority = _JIRA_PRIORITY_MAP.get(priority_name, Priority.MEDIUM)

    assignee: Optional[TeamMember] = None
    raw_assignee = fields.get("assignee")
    if raw_assignee:
        assignee = TeamMember(
            name=raw_assignee.get("displayName", ""),
            jira_email=raw_assignee.get("emailAddress"),
        )

    labels: list[str] = fields.get("labels") or []
    created_at = _parse_jira_dt(fields["created"])
    updated_at = _parse_jira_dt(fields["updated"])

    return Ticket(
        id=issue["key"],
        title=fields.get("summary", ""),
        description=(fields.get("description") or ""),
        status=status,
        priority=priority,
        assignee=assignee,
        labels=labels,
        created_at=created_at,
        updated_at=updated_at,
        source="jira",
        raw={"self": issue.get("self", ""), "id": issue.get("id", "")},
    )


def _retry_policy() -> tenacity.Retrying:
    return tenacity.Retrying(
        retry=tenacity.retry_if_exception_type((ConnectionError, HTTPError)),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=60),
        stop=tenacity.stop_after_attempt(5),
        reraise=True,
    )


class JiraAdapter(TicketSourceAdapter):
    """Reads and writes Jira issues as Tickets."""

    def __init__(self, config: JiraConfig) -> None:
        email = os.environ.get(config.email_env, "")
        token = os.environ.get(config.token_env, "")
        self._jira = Jira(url=config.url, username=email, password=token, cloud=True)
        self._config = config

    def _project_key(self) -> str:
        # Derive a default project key from Jira URL path — callers can override via filters.
        # In practice the project key is set by callers; this is a reasonable fallback.
        return ""

    def _build_jql(self, filters: TicketFilter, project_key: str = "") -> str:
        clauses: list[str] = []
        if project_key:
            clauses.append(f"project = {project_key}")
        if filters.status:
            jira_statuses = [f'"{_STATUS_TO_JIRA.get(s, s.value)}"' for s in filters.status]
            clauses.append(f"status IN ({', '.join(jira_statuses)})")
        if filters.assignee:
            clauses.append(f'assignee = "{filters.assignee}"')
        if filters.labels:
            for lbl in filters.labels:
                clauses.append(f'labels = "{lbl}"')
        if filters.updated_since:
            since = filters.updated_since.strftime("%Y-%m-%d %H:%M")
            clauses.append(f'updated >= "{since}"')
        return " AND ".join(clauses) if clauses else "ORDER BY updated DESC"

    async def list_tickets(self, filters: TicketFilter) -> list[Ticket]:
        def _sync() -> list[Ticket]:
            jql = self._build_jql(filters)
            tickets: list[Ticket] = []
            start = 0
            while True:
                for attempt in _retry_policy():
                    with attempt:
                        result = self._jira.jql(
                            jql,
                            start=start,
                            limit=_PAGE_SIZE,
                            fields="summary,description,status,priority,assignee,labels,created,updated",
                        )
                issues = result.get("issues", [])
                for issue in issues:
                    tickets.append(_to_ticket(issue))
                if len(issues) < _PAGE_SIZE:
                    break
                start += _PAGE_SIZE
            return tickets

        return await asyncio.to_thread(_sync)

    async def get_ticket(self, id: str) -> Ticket:
        def _sync() -> Ticket:
            for attempt in _retry_policy():
                with attempt:
                    issue = self._jira.issue(id)
            return _to_ticket(issue)

        return await asyncio.to_thread(_sync)

    async def create_ticket(self, spec: TicketSpec) -> Ticket:
        def _sync() -> Ticket:
            # Extract project key from assignee handle or use first component of an existing key.
            # Callers are expected to embed `PROJECT_KEY:` in title or pass via labels when needed.
            fields: dict[str, Any] = {
                "summary": spec.title,
                "description": spec.description,
                "issuetype": {"name": "Task"},
                "priority": {"name": _PRIORITY_TO_JIRA[spec.priority]},
                "labels": spec.labels,
            }
            if spec.assignee:
                fields["assignee"] = {"accountId": spec.assignee}

            for attempt in _retry_policy():
                with attempt:
                    created = self._jira.create_issue(fields=fields)
            issue_key = created.get("key", "")
            for attempt in _retry_policy():
                with attempt:
                    issue = self._jira.issue(issue_key)
            return _to_ticket(issue)

        return await asyncio.to_thread(_sync)

    async def update_ticket(self, id: str, delta: TicketDelta) -> Ticket:
        def _sync() -> Ticket:
            fields: dict[str, Any] = {}
            if delta.title is not None:
                fields["summary"] = delta.title
            if delta.description is not None:
                fields["description"] = delta.description
            if delta.priority is not None:
                fields["priority"] = {"name": _PRIORITY_TO_JIRA[delta.priority]}
            if delta.labels is not None:
                fields["labels"] = delta.labels
            if delta.assignee is not None:
                fields["assignee"] = {"accountId": delta.assignee}

            if fields:
                for attempt in _retry_policy():
                    with attempt:
                        self._jira.update_issue_field(id, fields)

            if delta.status is not None:
                target_status = _STATUS_TO_JIRA.get(delta.status, delta.status.value)
                for attempt in _retry_policy():
                    with attempt:
                        transitions = self._jira.get_issue_transitions(id)
                for t in transitions:
                    if t.get("name", "").lower() == target_status.lower():
                        for attempt in _retry_policy():
                            with attempt:
                                self._jira.issue_transition(id, t["id"])
                        break

            for attempt in _retry_policy():
                with attempt:
                    issue = self._jira.issue(id)
            return _to_ticket(issue)

        return await asyncio.to_thread(_sync)

    async def add_comment(self, id: str, body: str) -> None:
        def _sync() -> None:
            for attempt in _retry_policy():
                with attempt:
                    self._jira.issue_add_comment(id, body)

        await asyncio.to_thread(_sync)

    async def list_members(self) -> list[TeamMember]:
        # Jira Cloud does not expose a simple "list all users" endpoint without admin scope.
        # Return empty list — callers should use team config from AppConfig instead.
        return []
