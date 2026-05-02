"""Unit tests for ticket source adapters (GitHub + Jira).

All external API calls are mocked — no network or credentials needed.
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from pm_agent.adapters.ticket.models import (
    Priority,
    Ticket,
    TicketDelta,
    TicketFilter,
    TicketSpec,
    TicketStatus,
    TeamMember,
)
from pm_agent.adapters.ticket.github import (
    GitHubIssuesAdapter,
    _parse_priority,
    _parse_status,
)
from pm_agent.adapters.ticket.jira import JiraAdapter, _to_ticket as jira_to_ticket
from pm_agent.adapters.ticket.factory import get_ticket_adapter
from pm_agent.config.models import AppConfig, GitHubConfig, JiraConfig, TicketSourcesConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_github_issue(
    number: int = 1,
    title: str = "Fix login bug",
    body: str = "Users can't log in",
    state: str = "open",
    labels: list[str] | None = None,
    assignee_login: str | None = None,
    pull_request: Any = None,
) -> MagicMock:
    issue = MagicMock()
    issue.number = number
    issue.title = title
    issue.body = body
    issue.state = state
    issue.html_url = f"https://github.com/org/repo/issues/{number}"
    issue.node_id = f"I_{number}"
    issue.created_at = _NOW
    issue.updated_at = _NOW
    issue.pull_request = pull_request

    mock_labels = []
    for name in (labels or []):
        lbl = MagicMock()
        lbl.name = name
        mock_labels.append(lbl)
    issue.labels = mock_labels

    if assignee_login:
        assignee = MagicMock()
        assignee.login = assignee_login
        assignee.name = assignee_login
        issue.assignee = assignee
    else:
        issue.assignee = None

    return issue


def _make_github_config() -> GitHubConfig:
    return GitHubConfig(repo="org/repo", token_env="GITHUB_TOKEN")


def _make_jira_issue(
    key: str = "PROJ-1",
    summary: str = "Fix login bug",
    description: str = "Users can't log in",
    status: str = "Open",
    priority: str = "Medium",
    assignee_email: str | None = None,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "status": {"name": status},
        "priority": {"name": priority},
        "labels": labels or [],
        "created": "2024-06-01T12:00:00.000+0000",
        "updated": "2024-06-01T12:00:00.000+0000",
        "assignee": None,
    }
    if assignee_email:
        fields["assignee"] = {"displayName": assignee_email, "emailAddress": assignee_email}
    return {"key": key, "id": "10001", "self": f"https://jira.example.com/rest/api/2/issue/{key}", "fields": fields}


def _make_jira_config() -> JiraConfig:
    return JiraConfig(url="https://example.atlassian.net", email_env="JIRA_EMAIL", token_env="JIRA_TOKEN")


# ---------------------------------------------------------------------------
# Priority label parsing
# ---------------------------------------------------------------------------

class TestParsePriority:
    def test_parses_critical(self) -> None:
        assert _parse_priority(["priority:critical", "bug"]) == Priority.CRITICAL

    def test_parses_high(self) -> None:
        assert _parse_priority(["priority:high"]) == Priority.HIGH

    def test_parses_low(self) -> None:
        assert _parse_priority(["priority:low"]) == Priority.LOW

    def test_defaults_to_medium_when_no_priority_label(self) -> None:
        assert _parse_priority(["bug", "frontend"]) == Priority.MEDIUM

    def test_case_insensitive(self) -> None:
        assert _parse_priority(["Priority:HIGH"]) == Priority.HIGH


# ---------------------------------------------------------------------------
# Status parsing from GitHub issue
# ---------------------------------------------------------------------------

class TestParseStatus:
    def test_open_issue(self) -> None:
        issue = _make_github_issue(state="open")
        assert _parse_status(issue) == TicketStatus.OPEN

    def test_closed_issue(self) -> None:
        issue = _make_github_issue(state="closed")
        assert _parse_status(issue) == TicketStatus.CLOSED

    def test_in_progress_label_overrides_open_state(self) -> None:
        issue = _make_github_issue(state="open", labels=["in progress"])
        assert _parse_status(issue) == TicketStatus.IN_PROGRESS

    def test_blocked_label(self) -> None:
        issue = _make_github_issue(state="open", labels=["blocked"])
        assert _parse_status(issue) == TicketStatus.BLOCKED


# ---------------------------------------------------------------------------
# GitHubIssuesAdapter
# ---------------------------------------------------------------------------

class TestGitHubIssuesAdapter:
    def _make_adapter(self) -> GitHubIssuesAdapter:
        with patch("pm_agent.adapters.ticket.github.Github"):
            adapter = GitHubIssuesAdapter(_make_github_config())
        return adapter

    def _mock_repo(self, adapter: GitHubIssuesAdapter, issues: list[MagicMock]) -> MagicMock:
        repo = MagicMock()
        repo.get_issues.return_value = issues
        adapter._repo = repo
        return repo

    # --- list_tickets ---

    @pytest.mark.asyncio
    async def test_list_tickets_returns_tickets(self) -> None:
        adapter = self._make_adapter()
        issues = [
            _make_github_issue(number=1, labels=["priority:high"]),
            _make_github_issue(number=2, labels=["priority:low"]),
        ]
        self._mock_repo(adapter, issues)

        result = await adapter.list_tickets(TicketFilter())
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[0].priority == Priority.HIGH
        assert result[1].priority == Priority.LOW

    @pytest.mark.asyncio
    async def test_list_tickets_skips_pull_requests(self) -> None:
        adapter = self._make_adapter()
        pr = _make_github_issue(number=99, pull_request=MagicMock())
        issue = _make_github_issue(number=1)
        self._mock_repo(adapter, [pr, issue])

        result = await adapter.list_tickets(TicketFilter())
        assert len(result) == 1
        assert result[0].id == "1"

    @pytest.mark.asyncio
    async def test_list_tickets_open_filter_sets_state(self) -> None:
        adapter = self._make_adapter()
        self._mock_repo(adapter, [])

        await adapter.list_tickets(TicketFilter(status=[TicketStatus.OPEN]))
        adapter._repo.get_issues.assert_called_once()
        call_kwargs = adapter._repo.get_issues.call_args.kwargs
        assert call_kwargs["state"] == "open"

    @pytest.mark.asyncio
    async def test_list_tickets_closed_filter(self) -> None:
        adapter = self._make_adapter()
        self._mock_repo(adapter, [])

        await adapter.list_tickets(TicketFilter(status=[TicketStatus.CLOSED]))
        call_kwargs = adapter._repo.get_issues.call_args.kwargs
        assert call_kwargs["state"] == "closed"

    @pytest.mark.asyncio
    async def test_list_tickets_mixed_status_filter_uses_all(self) -> None:
        adapter = self._make_adapter()
        self._mock_repo(adapter, [])

        await adapter.list_tickets(TicketFilter(status=[TicketStatus.OPEN, TicketStatus.CLOSED]))
        call_kwargs = adapter._repo.get_issues.call_args.kwargs
        assert call_kwargs["state"] == "all"

    # --- get_ticket ---

    @pytest.mark.asyncio
    async def test_get_ticket_returns_correct_ticket(self) -> None:
        adapter = self._make_adapter()
        repo = MagicMock()
        issue = _make_github_issue(number=42, title="Deploy failure", labels=["priority:critical"])
        repo.get_issue.return_value = issue
        adapter._repo = repo

        result = await adapter.get_ticket("42")
        assert result.id == "42"
        assert result.title == "Deploy failure"
        assert result.priority == Priority.CRITICAL

    # --- create_ticket ---

    @pytest.mark.asyncio
    async def test_create_ticket_encodes_priority_label(self) -> None:
        adapter = self._make_adapter()
        repo = MagicMock()
        created_issue = _make_github_issue(number=10, labels=["bug", "priority:high"])
        repo.create_issue.return_value = created_issue
        adapter._repo = repo

        spec = TicketSpec(title="New feature", description="Desc", priority=Priority.HIGH, labels=["bug"])
        result = await adapter.create_ticket(spec)

        call_kwargs = repo.create_issue.call_args.kwargs
        assert "priority:high" in call_kwargs["labels"]
        assert result.id == "10"

    @pytest.mark.asyncio
    async def test_create_ticket_with_assignee(self) -> None:
        adapter = self._make_adapter()
        repo = MagicMock()
        created_issue = _make_github_issue(number=5, assignee_login="alice")
        repo.create_issue.return_value = created_issue
        adapter._repo = repo

        spec = TicketSpec(title="Task", description="", assignee="alice")
        result = await adapter.create_ticket(spec)
        assert result.assignee is not None
        assert result.assignee.github_handle == "alice"

    # --- update_ticket ---

    @pytest.mark.asyncio
    async def test_update_ticket_closes_issue(self) -> None:
        adapter = self._make_adapter()
        repo = MagicMock()
        issue = _make_github_issue(number=3)
        updated_issue = _make_github_issue(number=3, state="closed")
        repo.get_issue.side_effect = [issue, updated_issue]
        adapter._repo = repo

        result = await adapter.update_ticket("3", TicketDelta(status=TicketStatus.CLOSED))
        issue.edit.assert_called_once()
        assert result.status == TicketStatus.CLOSED

    @pytest.mark.asyncio
    async def test_update_ticket_changes_priority_label(self) -> None:
        adapter = self._make_adapter()
        repo = MagicMock()
        issue = _make_github_issue(number=4, labels=["bug", "priority:low"])
        updated_issue = _make_github_issue(number=4, labels=["bug", "priority:high"])
        repo.get_issue.side_effect = [issue, updated_issue]
        adapter._repo = repo

        result = await adapter.update_ticket("4", TicketDelta(priority=Priority.HIGH))
        call_kwargs = issue.edit.call_args.kwargs
        assert "priority:high" in call_kwargs["labels"]
        assert "priority:low" not in call_kwargs["labels"]

    # --- add_comment ---

    @pytest.mark.asyncio
    async def test_add_comment_calls_create_comment(self) -> None:
        adapter = self._make_adapter()
        repo = MagicMock()
        issue = _make_github_issue(number=7)
        repo.get_issue.return_value = issue
        adapter._repo = repo

        await adapter.add_comment("7", "LGTM")
        issue.create_comment.assert_called_once_with("LGTM")

    # --- list_members ---

    @pytest.mark.asyncio
    async def test_list_members_returns_team_members(self) -> None:
        adapter = self._make_adapter()
        repo = MagicMock()
        collaborator = MagicMock()
        collaborator.login = "bob"
        collaborator.name = "Bob"
        repo.get_collaborators.return_value = [collaborator]
        adapter._repo = repo

        members = await adapter.list_members()
        assert len(members) == 1
        assert members[0].github_handle == "bob"

    # --- tenacity retry on rate limit ---

    @pytest.mark.asyncio
    async def test_list_tickets_retries_on_rate_limit(self) -> None:
        from github import RateLimitExceededException

        adapter = self._make_adapter()
        repo = MagicMock()
        # First call raises, second returns normally
        repo.get_issues.side_effect = [
            RateLimitExceededException(403, {"message": "rate limited"}, {}),
            [_make_github_issue(number=1)],
        ]
        adapter._repo = repo

        result = await adapter.list_tickets(TicketFilter())
        assert len(result) == 1
        assert repo.get_issues.call_count == 2

    # --- source field ---

    @pytest.mark.asyncio
    async def test_ticket_source_is_github(self) -> None:
        adapter = self._make_adapter()
        repo = MagicMock()
        repo.get_issues.return_value = [_make_github_issue(number=1)]
        adapter._repo = repo

        tickets = await adapter.list_tickets(TicketFilter())
        assert tickets[0].source == "github"


# ---------------------------------------------------------------------------
# JiraAdapter — _to_ticket mapping
# ---------------------------------------------------------------------------

class TestJiraToTicket:
    def test_open_status_maps_correctly(self) -> None:
        issue = _make_jira_issue(status="Open")
        ticket = jira_to_ticket(issue)
        assert ticket.status == TicketStatus.OPEN

    def test_in_progress_status(self) -> None:
        issue = _make_jira_issue(status="In Progress")
        ticket = jira_to_ticket(issue)
        assert ticket.status == TicketStatus.IN_PROGRESS

    def test_done_maps_to_closed(self) -> None:
        issue = _make_jira_issue(status="Done")
        ticket = jira_to_ticket(issue)
        assert ticket.status == TicketStatus.CLOSED

    def test_high_priority(self) -> None:
        issue = _make_jira_issue(priority="High")
        ticket = jira_to_ticket(issue)
        assert ticket.priority == Priority.HIGH

    def test_highest_maps_to_critical(self) -> None:
        issue = _make_jira_issue(priority="Highest")
        ticket = jira_to_ticket(issue)
        assert ticket.priority == Priority.CRITICAL

    def test_assignee_parsed(self) -> None:
        issue = _make_jira_issue(assignee_email="dev@example.com")
        ticket = jira_to_ticket(issue)
        assert ticket.assignee is not None
        assert ticket.assignee.jira_email == "dev@example.com"

    def test_no_assignee(self) -> None:
        issue = _make_jira_issue()
        ticket = jira_to_ticket(issue)
        assert ticket.assignee is None

    def test_labels_parsed(self) -> None:
        issue = _make_jira_issue(labels=["backend", "urgent"])
        ticket = jira_to_ticket(issue)
        assert "backend" in ticket.labels
        assert "urgent" in ticket.labels

    def test_source_is_jira(self) -> None:
        ticket = jira_to_ticket(_make_jira_issue())
        assert ticket.source == "jira"

    def test_id_is_issue_key(self) -> None:
        ticket = jira_to_ticket(_make_jira_issue(key="PROJ-42"))
        assert ticket.id == "PROJ-42"

    def test_unknown_status_defaults_to_open(self) -> None:
        issue = _make_jira_issue(status="Weird Custom Status")
        ticket = jira_to_ticket(issue)
        assert ticket.status == TicketStatus.OPEN


# ---------------------------------------------------------------------------
# JiraAdapter — API methods
# ---------------------------------------------------------------------------

class TestJiraAdapter:
    def _make_adapter(self) -> JiraAdapter:
        with patch("pm_agent.adapters.ticket.jira.Jira"):
            adapter = JiraAdapter(_make_jira_config())
        return adapter

    @pytest.mark.asyncio
    async def test_list_tickets_single_page(self) -> None:
        adapter = self._make_adapter()
        issues = [_make_jira_issue(key=f"PROJ-{i}") for i in range(3)]
        adapter._jira.jql.return_value = {"issues": issues}

        result = await adapter.list_tickets(TicketFilter())
        assert len(result) == 3
        assert result[0].id == "PROJ-0"

    @pytest.mark.asyncio
    async def test_list_tickets_pagination(self) -> None:
        adapter = self._make_adapter()
        page1 = [_make_jira_issue(key=f"PROJ-{i}") for i in range(50)]
        page2 = [_make_jira_issue(key=f"PROJ-{i}") for i in range(50, 55)]
        adapter._jira.jql.side_effect = [
            {"issues": page1},
            {"issues": page2},
        ]

        result = await adapter.list_tickets(TicketFilter())
        assert len(result) == 55

    @pytest.mark.asyncio
    async def test_get_ticket(self) -> None:
        adapter = self._make_adapter()
        adapter._jira.issue.return_value = _make_jira_issue(key="PROJ-10", summary="Important task")

        result = await adapter.get_ticket("PROJ-10")
        assert result.id == "PROJ-10"
        assert result.title == "Important task"

    @pytest.mark.asyncio
    async def test_create_ticket(self) -> None:
        adapter = self._make_adapter()
        adapter._jira.create_issue.return_value = {"key": "PROJ-99"}
        adapter._jira.issue.return_value = _make_jira_issue(key="PROJ-99", summary="New task")

        spec = TicketSpec(title="New task", description="Do the thing", priority=Priority.HIGH)
        result = await adapter.create_ticket(spec)
        assert result.id == "PROJ-99"

        call_kwargs = adapter._jira.create_issue.call_args.kwargs
        assert call_kwargs["fields"]["priority"]["name"] == "High"

    @pytest.mark.asyncio
    async def test_update_ticket_fields(self) -> None:
        adapter = self._make_adapter()
        adapter._jira.issue.return_value = _make_jira_issue(key="PROJ-5", summary="Updated")

        result = await adapter.update_ticket("PROJ-5", TicketDelta(title="Updated"))
        adapter._jira.update_issue_field.assert_called_once()
        assert result.id == "PROJ-5"

    @pytest.mark.asyncio
    async def test_update_ticket_status_triggers_transition(self) -> None:
        adapter = self._make_adapter()
        adapter._jira.get_issue_transitions.return_value = [
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
        adapter._jira.issue.return_value = _make_jira_issue(key="PROJ-6", status="Done")

        await adapter.update_ticket("PROJ-6", TicketDelta(status=TicketStatus.CLOSED))
        adapter._jira.issue_transition.assert_called_once_with("PROJ-6", "31")

    @pytest.mark.asyncio
    async def test_add_comment(self) -> None:
        adapter = self._make_adapter()
        await adapter.add_comment("PROJ-1", "Fixed in PR #42")
        adapter._jira.issue_add_comment.assert_called_once_with("PROJ-1", "Fixed in PR #42")

    @pytest.mark.asyncio
    async def test_list_members_returns_empty(self) -> None:
        adapter = self._make_adapter()
        members = await adapter.list_members()
        assert members == []

    @pytest.mark.asyncio
    async def test_list_tickets_retries_on_connection_error(self) -> None:
        from requests.exceptions import ConnectionError as ReqConnError

        adapter = self._make_adapter()
        adapter._jira.jql.side_effect = [
            ReqConnError("timeout"),
            {"issues": [_make_jira_issue()]},
        ]

        result = await adapter.list_tickets(TicketFilter())
        assert len(result) == 1
        assert adapter._jira.jql.call_count == 2


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestGetTicketAdapter:
    def _base_config(self) -> dict:
        return {
            "project": {"name": "test"},
            "ticket_sources": {"primary": "github", "github": {"repo": "org/repo"}},
            "llm": {
                "fast": {"provider": "gemini", "model": "models/gemini-2.0-flash"},
                "mid": {"provider": "gemini", "model": "models/gemini-2.5-pro"},
                "strong": {"provider": "claude", "model": "claude-opus-4-20250514"},
            },
        }

    def test_returns_github_adapter(self) -> None:
        with patch("pm_agent.adapters.ticket.github.Github"):
            cfg = AppConfig.model_validate(self._base_config())
            adapter = get_ticket_adapter(cfg)
        assert isinstance(adapter, GitHubIssuesAdapter)

    def test_returns_jira_adapter(self) -> None:
        raw = self._base_config()
        raw["ticket_sources"]["primary"] = "jira"
        raw["ticket_sources"]["jira"] = {
            "url": "https://example.atlassian.net",
        }
        with patch("pm_agent.adapters.ticket.jira.Jira"):
            cfg = AppConfig.model_validate(raw)
            adapter = get_ticket_adapter(cfg)
        assert isinstance(adapter, JiraAdapter)

    def test_raises_when_github_config_missing(self) -> None:
        raw = self._base_config()
        raw["ticket_sources"]["github"] = None
        cfg = AppConfig.model_validate(raw)
        with pytest.raises(ValueError, match="ticket_sources.github must be set"):
            get_ticket_adapter(cfg)

    def test_raises_on_unknown_source(self) -> None:
        raw = self._base_config()
        raw["ticket_sources"]["primary"] = "linear"  # type: ignore[assignment]
        with pytest.raises(Exception):
            AppConfig.model_validate(raw)
