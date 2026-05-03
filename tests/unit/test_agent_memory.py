"""
Unit tests for AgentMemoryStore / SQLiteAgentMemoryStore (Phase 3, Task 3.5).
Uses a temporary in-memory (or temp-file) SQLite DB — no persistent side-effects.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from pm_agent.context.memory.base import RitualMemoryEntry
from pm_agent.context.memory.sqlite import SQLiteAgentMemoryStore


def _entry(
    ritual_name: str = "standup_agenda",
    sdlc_mode: str = "sdd",
    trigger: str = "cron",
    outcome_summary: str = "Agenda generated. #5 blocked.",
    tickets_affected: list | None = None,
    decisions: list | None = None,
    model_used: str = "models/gemini-2.0-flash",
    compression_occurred: bool = False,
    executed_at: datetime | None = None,
) -> RitualMemoryEntry:
    kwargs = dict(
        ritual_name=ritual_name,
        sdlc_mode=sdlc_mode,
        trigger=trigger,
        outcome_summary=outcome_summary,
        tickets_affected=tickets_affected or [],
        decisions=decisions or [],
        model_used=model_used,
        compression_occurred=compression_occurred,
    )
    if executed_at:
        kwargs["executed_at"] = executed_at
    return RitualMemoryEntry(**kwargs)


@pytest.fixture
def store(tmp_path: Path) -> SQLiteAgentMemoryStore:
    db_file = tmp_path / "test_memory.db"
    return SQLiteAgentMemoryStore(db_path=str(db_file))


# ---------------------------------------------------------------------------
# Write + read round-trip
# ---------------------------------------------------------------------------

class TestWriteReadRoundTrip:
    @pytest.mark.asyncio
    async def test_written_entry_retrievable(self, store):
        e = _entry(outcome_summary="Sprint on track.")
        await store.write(e)
        results = await store.get_recent("standup_agenda")
        assert len(results) == 1
        assert results[0].outcome_summary == "Sprint on track."

    @pytest.mark.asyncio
    async def test_id_preserved(self, store):
        e = _entry()
        await store.write(e)
        results = await store.get_recent("standup_agenda")
        assert results[0].id == e.id

    @pytest.mark.asyncio
    async def test_tickets_affected_list_preserved(self, store):
        e = _entry(tickets_affected=["#1", "#5", "#12"])
        await store.write(e)
        results = await store.get_recent("standup_agenda")
        assert results[0].tickets_affected == ["#1", "#5", "#12"]

    @pytest.mark.asyncio
    async def test_decisions_list_preserved(self, store):
        e = _entry(decisions=["#15 escalated to manager", "#8 reassigned to Alice"])
        await store.write(e)
        results = await store.get_recent("standup_agenda")
        assert results[0].decisions == ["#15 escalated to manager", "#8 reassigned to Alice"]

    @pytest.mark.asyncio
    async def test_compression_occurred_bool_preserved(self, store):
        e = _entry(compression_occurred=True)
        await store.write(e)
        results = await store.get_recent("standup_agenda")
        assert results[0].compression_occurred is True

    @pytest.mark.asyncio
    async def test_empty_lists_preserved(self, store):
        e = _entry(tickets_affected=[], decisions=[])
        await store.write(e)
        results = await store.get_recent("standup_agenda")
        assert results[0].tickets_affected == []
        assert results[0].decisions == []


# ---------------------------------------------------------------------------
# Ordering — newest first
# ---------------------------------------------------------------------------

class TestOrderingNewestFirst:
    @pytest.mark.asyncio
    async def test_entries_returned_newest_first(self, store):
        t1 = datetime(2026, 4, 29, 9, 0, 0)
        t2 = datetime(2026, 4, 30, 9, 0, 0)
        t3 = datetime(2026, 5, 1, 9, 0, 0)
        for ts, summary in [(t1, "Day 1"), (t2, "Day 2"), (t3, "Day 3")]:
            await store.write(_entry(outcome_summary=summary, executed_at=ts))
        results = await store.get_recent("standup_agenda", limit=3)
        assert [r.outcome_summary for r in results] == ["Day 3", "Day 2", "Day 1"]

    @pytest.mark.asyncio
    async def test_limit_respected(self, store):
        for i in range(5):
            await store.write(_entry(outcome_summary=f"run {i}"))
        results = await store.get_recent("standup_agenda", limit=3)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# Ritual name isolation
# ---------------------------------------------------------------------------

class TestRitualNameIsolation:
    @pytest.mark.asyncio
    async def test_entries_for_different_rituals_not_mixed(self, store):
        await store.write(_entry(ritual_name="standup_agenda", outcome_summary="Standup."))
        await store.write(_entry(ritual_name="task_creator", outcome_summary="Tasks created."))
        standup_results = await store.get_recent("standup_agenda")
        task_results = await store.get_recent("task_creator")
        assert all(r.ritual_name == "standup_agenda" for r in standup_results)
        assert all(r.ritual_name == "task_creator" for r in task_results)

    @pytest.mark.asyncio
    async def test_empty_result_for_unknown_ritual(self, store):
        results = await store.get_recent("nonexistent_ritual")
        assert results == []


# ---------------------------------------------------------------------------
# get_context_injection format
# ---------------------------------------------------------------------------

class TestContextInjectionFormat:
    @pytest.mark.asyncio
    async def test_returns_empty_string_when_no_entries(self, store):
        result = await store.get_context_injection("standup_agenda")
        assert result == ""

    @pytest.mark.asyncio
    async def test_injection_contains_ritual_name(self, store):
        await store.write(_entry())
        result = await store.get_context_injection("standup_agenda")
        assert "standup_agenda" in result

    @pytest.mark.asyncio
    async def test_injection_contains_outcome_summary(self, store):
        await store.write(_entry(outcome_summary="Agenda done. #3 blocked."))
        result = await store.get_context_injection("standup_agenda")
        assert "Agenda done. #3 blocked." in result

    @pytest.mark.asyncio
    async def test_injection_contains_trigger(self, store):
        await store.write(_entry(trigger="cron"))
        result = await store.get_context_injection("standup_agenda")
        assert "[cron]" in result

    @pytest.mark.asyncio
    async def test_injection_limited_to_three_entries(self, store):
        for i in range(5):
            await store.write(_entry(outcome_summary=f"run {i}"))
        result = await store.get_context_injection("standup_agenda")
        # Only 3 bullet lines expected
        bullet_lines = [line for line in result.splitlines() if line.startswith("- ")]
        assert len(bullet_lines) == 3

    @pytest.mark.asyncio
    async def test_injection_header_format(self, store):
        await store.write(_entry())
        result = await store.get_context_injection("standup_agenda")
        assert result.startswith("RECENT RITUAL HISTORY")
