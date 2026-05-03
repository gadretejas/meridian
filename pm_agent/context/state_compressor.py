"""
StateCompressor — LangGraph node.

Trims PMAgentState when field sizes exceed configured thresholds.
Plug this between execute_ritual and evaluate_autonomy in the graph (Phase 7).

Returns the full state dict so LangGraph replaces the whole state rather
than merging partial updates — ticket and trace fields are replaced, not appended.
"""

import structlog

from pm_agent.adapters.ticket.models import TicketSummary
from pm_agent.config.loader import load_config
from pm_agent.core.state import PMAgentState

log = structlog.get_logger()


def compress_state(state: PMAgentState) -> dict:
    """
    LangGraph node that trims oversized state fields.

    Tickets beyond the threshold are converted to lightweight TicketSummary
    objects. The execution trace is trimmed to the last N entries.
    Sets state_compressed=True if any trimming occurred.

    Args:
        state: Current PMAgentState dict from the LangGraph graph.

    Returns:
        Updated state dict (returned as plain dict for LangGraph compatibility).
    """
    cfg = load_config().context_management.state_compressor
    updated = dict(**state)
    compressed = False

    tickets = state.get("tickets", [])
    if len(tickets) > cfg.max_tickets_in_state:
        updated["tickets"] = [
            TicketSummary(
                id=t.id,
                title=t.title,
                status=t.status,
                priority=t.priority,
            )
            for t in tickets
        ]
        compressed = True
        log.info(
            "state_tickets_compressed",
            original_count=len(tickets),
            limit=cfg.max_tickets_in_state,
        )

    trace = state.get("execution_trace", [])
    if len(trace) > cfg.max_trace_entries:
        omitted = len(trace) - cfg.trace_keep_last
        tail = trace[-cfg.trace_keep_last:]
        updated["execution_trace"] = [
            f"[TRACE COMPRESSED: {omitted} entries omitted]"
        ] + tail
        compressed = True
        log.info(
            "state_trace_compressed",
            original_count=len(trace),
            omitted=omitted,
        )

    if compressed:
        updated["state_compressed"] = True

    return updated
