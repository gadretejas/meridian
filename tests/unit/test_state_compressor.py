"""
Unit tests for compress_state LangGraph node (Phase 3, Task 3.4).
"""

from datetime import datetime

import pytest

from pm_agent.adapters.ticket.models import Priority, Ticket, TicketStatus, TicketSummary
from pm_agent.context.state_compressor import compress_state
from pm_agent.core.state import make_initial_state

_NOW = datetime(2026, 5, 3, 9, 0, 0)


def _make_ticket(i: int) -> Ticket:
    return Ticket(
        id=f"#{i}",
        title=f"Ticket {i}",
        description=f"Description for ticket {i}",
        status=TicketStatus.OPEN,
        priority=Priority.MEDIUM,
        created_at=_NOW,
        updated_at=_NOW,
        source="github",
    )


def _state_with_tickets(n: int) -> dict:
    state = make_initial_state("standup_agenda")
    state["tickets"] = [_make_ticket(i) for i in range(n)]
    return state


def _state_with_trace(n: int) -> dict:
    state = make_initial_state("standup_agenda")
    state["execution_trace"] = [f"step {i}" for i in range(n)]
    return state


# ---------------------------------------------------------------------------
# Ticket compression
# ---------------------------------------------------------------------------

class TestTicketCompression:
    def test_tickets_below_threshold_not_compressed(self):
        """Default max_tickets_in_state=50; 10 tickets — no compression."""
        state = _state_with_tickets(10)
        result = compress_state(state)
        assert all(isinstance(t, Ticket) for t in result["tickets"])
        assert result.get("state_compressed") is not True

    def test_tickets_above_threshold_converted_to_summaries(self):
        """51 tickets — converted to TicketSummary objects."""
        state = _state_with_tickets(51)
        result = compress_state(state)
        assert all(isinstance(t, TicketSummary) for t in result["tickets"])

    def test_ticket_summary_preserves_key_fields(self):
        state = _state_with_tickets(51)
        result = compress_state(state)
        first = result["tickets"][0]
        assert first.id == "#0"
        assert first.title == "Ticket 0"
        assert first.status == TicketStatus.OPEN
        assert first.priority == Priority.MEDIUM

    def test_state_compressed_flag_set_after_ticket_compression(self):
        state = _state_with_tickets(51)
        result = compress_state(state)
        assert result["state_compressed"] is True

    def test_state_compressed_flag_not_set_when_no_compression(self):
        state = _state_with_tickets(5)
        result = compress_state(state)
        assert result.get("state_compressed") is not True

    def test_ticket_count_preserved_after_compression(self):
        state = _state_with_tickets(60)
        result = compress_state(state)
        assert len(result["tickets"]) == 60


# ---------------------------------------------------------------------------
# Trace compression
# ---------------------------------------------------------------------------

class TestTraceCompression:
    def test_trace_below_threshold_not_trimmed(self):
        """Default max_trace_entries=100; 50 entries — no trimming."""
        state = _state_with_trace(50)
        result = compress_state(state)
        assert len(result["execution_trace"]) == 50
        assert result.get("state_compressed") is not True

    def test_trace_above_threshold_trimmed(self):
        """101 entries — trimmed to trace_keep_last (default 20) + 1 summary entry."""
        state = _state_with_trace(101)
        result = compress_state(state)
        assert len(result["execution_trace"]) == 21  # 1 summary + 20 tail

    def test_trace_summary_entry_prefix(self):
        state = _state_with_trace(101)
        result = compress_state(state)
        assert result["execution_trace"][0].startswith("[TRACE COMPRESSED:")

    def test_trace_tail_entries_are_last_n(self):
        """The kept entries are the last trace_keep_last (20) steps."""
        state = _state_with_trace(110)
        result = compress_state(state)
        kept = result["execution_trace"][1:]  # skip the summary header
        assert kept == [f"step {i}" for i in range(90, 110)]

    def test_state_compressed_flag_set_after_trace_compression(self):
        state = _state_with_trace(101)
        result = compress_state(state)
        assert result["state_compressed"] is True


# ---------------------------------------------------------------------------
# Both fields exceed thresholds simultaneously
# ---------------------------------------------------------------------------

class TestBothExceedThresholds:
    def test_both_tickets_and_trace_compressed_together(self):
        state = make_initial_state("standup_agenda")
        state["tickets"] = [_make_ticket(i) for i in range(55)]
        state["execution_trace"] = [f"step {i}" for i in range(105)]
        result = compress_state(state)
        assert all(isinstance(t, TicketSummary) for t in result["tickets"])
        assert result["execution_trace"][0].startswith("[TRACE COMPRESSED:")
        assert result["state_compressed"] is True


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_dict(self):
        state = make_initial_state("standup_agenda")
        result = compress_state(state)
        assert isinstance(result, dict)

    def test_other_state_fields_preserved(self):
        state = make_initial_state("standup_agenda", sdlc_mode="agile", trigger="cron")
        result = compress_state(state)
        assert result["ritual_name"] == "standup_agenda"
        assert result["sdlc_mode"] == "agile"
        assert result["trigger"] == "cron"
