import asyncio
import os
from datetime import timezone
from typing import Optional

import tenacity
from github import Github, GithubException, RateLimitExceededException
from github.Issue import Issue
from github.Repository import Repository

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
from pm_agent.config.models import GitHubConfig
from pm_agent.core.logging import get_logger

logger = get_logger(__name__)

# Labels the adapter reads/writes for priority — GitHub has no native priority field.
_PRIORITY_LABEL_PREFIX = "priority:"
_PRIORITY_MAP: dict[str, Priority] = {
    "priority:critical": Priority.CRITICAL,
    "priority:high": Priority.HIGH,
    "priority:medium": Priority.MEDIUM,
    "priority:low": Priority.LOW,
}
_STATUS_MAP: dict[str, TicketStatus] = {
    "open": TicketStatus.OPEN,
    "closed": TicketStatus.CLOSED,
}
_LABEL_STATUS_MAP: dict[str, TicketStatus] = {
    "in progress": TicketStatus.IN_PROGRESS,
    "in-progress": TicketStatus.IN_PROGRESS,
    "blocked": TicketStatus.BLOCKED,
}


def _parse_priority(labels: list[str]) -> Priority:
    for label in labels:
        if label.lower() in _PRIORITY_MAP:
            return _PRIORITY_MAP[label.lower()]
    return Priority.MEDIUM


def _parse_status(issue: Issue) -> TicketStatus:
    label_names = [lbl.name.lower() for lbl in issue.labels]
    for name in label_names:
        if name in _LABEL_STATUS_MAP:
            return _LABEL_STATUS_MAP[name]
    return _STATUS_MAP.get(issue.state, TicketStatus.OPEN)


def _to_ticket(issue: Issue, repo_name: str) -> Ticket:
    label_names = [lbl.name for lbl in issue.labels]
    assignee: Optional[TeamMember] = None
    if issue.assignee:
        assignee = TeamMember(name=issue.assignee.login, github_handle=issue.assignee.login)

    created = issue.created_at
    updated = issue.updated_at
    # PyGithub datetimes are timezone-aware (UTC); ensure consistency
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)

    return Ticket(
        id=str(issue.number),
        title=issue.title,
        description=issue.body or "",
        status=_parse_status(issue),
        priority=_parse_priority(label_names),
        assignee=assignee,
        labels=label_names,
        created_at=created,
        updated_at=updated,
        source="github",
        raw={
            "html_url": issue.html_url,
            "repo": repo_name,
            "node_id": issue.node_id,
        },
    )


def _retry_policy() -> tenacity.Retrying:
    return tenacity.Retrying(
        retry=tenacity.retry_if_exception_type((RateLimitExceededException, GithubException)),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=60),
        stop=tenacity.stop_after_attempt(5),
        reraise=True,
    )


class GitHubIssuesAdapter(TicketSourceAdapter):
    """Reads and writes GitHub Issues as Tickets.

    Priority is encoded in labels using the `priority:<level>` convention.
    """

    def __init__(self, config: GitHubConfig) -> None:
        token = os.environ.get(config.token_env, "")
        self._gh = Github(token) if token else Github()
        self._repo_name = config.repo
        self._repo: Optional[Repository] = None

    def _get_repo(self) -> Repository:
        if self._repo is None:
            self._repo = self._gh.get_repo(self._repo_name)
        return self._repo

    async def list_tickets(self, filters: TicketFilter) -> list[Ticket]:
        def _sync() -> list[Ticket]:
            repo = self._get_repo()
            kwargs: dict = {}

            # GitHub API state: "open", "closed", "all"
            if filters.status:
                has_closed = TicketStatus.CLOSED in filters.status
                has_open = any(s != TicketStatus.CLOSED for s in filters.status)
                if has_closed and has_open:
                    kwargs["state"] = "all"
                elif has_closed:
                    kwargs["state"] = "closed"
                else:
                    kwargs["state"] = "open"
            else:
                kwargs["state"] = "open"

            if filters.assignee:
                kwargs["assignee"] = filters.assignee
            if filters.labels:
                kwargs["labels"] = [repo.get_label(lbl) for lbl in filters.labels]
            if filters.updated_since:
                kwargs["since"] = filters.updated_since

            tickets: list[Ticket] = []
            for attempt in _retry_policy():
                with attempt:
                    for issue in repo.get_issues(**kwargs):
                        # Skip pull requests (GitHub returns PRs via issues API)
                        if issue.pull_request:
                            continue
                        ticket = _to_ticket(issue, self._repo_name)
                        # Post-filter by status if caller specified multiple states
                        if filters.status and ticket.status not in filters.status:
                            continue
                        tickets.append(ticket)
            return tickets

        return await asyncio.to_thread(_sync)

    async def get_ticket(self, id: str) -> Ticket:
        def _sync() -> Ticket:
            repo = self._get_repo()
            for attempt in _retry_policy():
                with attempt:
                    issue = repo.get_issue(int(id))
            return _to_ticket(issue, self._repo_name)

        return await asyncio.to_thread(_sync)

    async def create_ticket(self, spec: TicketSpec) -> Ticket:
        def _sync() -> Ticket:
            repo = self._get_repo()
            labels = list(spec.labels)
            # Encode priority as a label
            labels.append(f"priority:{spec.priority.value}")

            kwargs: dict = {"title": spec.title, "body": spec.description}
            if labels:
                kwargs["labels"] = labels
            if spec.assignee:
                kwargs["assignee"] = spec.assignee

            for attempt in _retry_policy():
                with attempt:
                    issue = repo.create_issue(**kwargs)
            return _to_ticket(issue, self._repo_name)

        return await asyncio.to_thread(_sync)

    async def update_ticket(self, id: str, delta: TicketDelta) -> Ticket:
        def _sync() -> Ticket:
            repo = self._get_repo()
            for attempt in _retry_policy():
                with attempt:
                    issue = repo.get_issue(int(id))

            edit_kwargs: dict = {}
            if delta.title is not None:
                edit_kwargs["title"] = delta.title
            if delta.description is not None:
                edit_kwargs["body"] = delta.description
            if delta.status is not None:
                edit_kwargs["state"] = "closed" if delta.status == TicketStatus.CLOSED else "open"
            if delta.labels is not None:
                # Preserve existing non-priority labels, replace priority label
                existing = [lbl.name for lbl in issue.labels if not lbl.name.startswith(_PRIORITY_LABEL_PREFIX)]
                new_labels = list(delta.labels) + existing
                if delta.priority is not None:
                    new_labels.append(f"priority:{delta.priority.value}")
                edit_kwargs["labels"] = new_labels
            elif delta.priority is not None:
                # Only priority changed — patch just the priority label
                non_priority = [lbl.name for lbl in issue.labels if not lbl.name.startswith(_PRIORITY_LABEL_PREFIX)]
                edit_kwargs["labels"] = non_priority + [f"priority:{delta.priority.value}"]
            if delta.assignee is not None:
                edit_kwargs["assignee"] = delta.assignee

            for attempt in _retry_policy():
                with attempt:
                    issue.edit(**edit_kwargs)
                    issue = repo.get_issue(int(id))  # re-fetch updated state
            return _to_ticket(issue, self._repo_name)

        return await asyncio.to_thread(_sync)

    async def add_comment(self, id: str, body: str) -> None:
        def _sync() -> None:
            repo = self._get_repo()
            for attempt in _retry_policy():
                with attempt:
                    issue = repo.get_issue(int(id))
                    issue.create_comment(body)

        await asyncio.to_thread(_sync)

    async def list_members(self) -> list[TeamMember]:
        def _sync() -> list[TeamMember]:
            repo = self._get_repo()
            members: list[TeamMember] = []
            for attempt in _retry_policy():
                with attempt:
                    for collaborator in repo.get_collaborators():
                        members.append(
                            TeamMember(
                                name=collaborator.name or collaborator.login,
                                github_handle=collaborator.login,
                            )
                        )
            return members

        return await asyncio.to_thread(_sync)
