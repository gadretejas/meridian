from pm_agent.adapters.ticket.base import TicketSourceAdapter
from pm_agent.adapters.ticket.github import GitHubIssuesAdapter
from pm_agent.adapters.ticket.jira import JiraAdapter
from pm_agent.config.models import AppConfig


def get_ticket_adapter(config: AppConfig) -> TicketSourceAdapter:
    source = config.ticket_sources.primary
    if source == "github":
        if config.ticket_sources.github is None:
            raise ValueError("ticket_sources.github must be set when primary source is 'github'")
        return GitHubIssuesAdapter(config.ticket_sources.github)
    if source == "jira":
        if config.ticket_sources.jira is None:
            raise ValueError("ticket_sources.jira must be set when primary source is 'jira'")
        return JiraAdapter(config.ticket_sources.jira)
    raise ValueError(f"Unknown ticket source: {source}")
