"""
SQLite-backed AgentMemoryStore.

Single table `ritual_memory` in an aiosqlite database.
The DB file is created on first write if it doesn't exist.
"""

import json
from datetime import datetime
from pathlib import Path

import aiosqlite

from pm_agent.context.memory.base import AgentMemoryStore, RitualMemoryEntry

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ritual_memory (
    id                  TEXT PRIMARY KEY,
    ritual_name         TEXT NOT NULL,
    sdlc_mode           TEXT NOT NULL,
    executed_at         TEXT NOT NULL,
    trigger             TEXT NOT NULL,
    outcome_summary     TEXT NOT NULL,
    tickets_affected    TEXT NOT NULL,
    decisions           TEXT NOT NULL,
    model_used          TEXT NOT NULL,
    compression_occurred INTEGER NOT NULL
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ritual_name
    ON ritual_memory(ritual_name, executed_at DESC);
"""

_INSERT = """
INSERT INTO ritual_memory
    (id, ritual_name, sdlc_mode, executed_at, trigger,
     outcome_summary, tickets_affected, decisions, model_used, compression_occurred)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

_SELECT_RECENT = """
SELECT id, ritual_name, sdlc_mode, executed_at, trigger,
       outcome_summary, tickets_affected, decisions, model_used, compression_occurred
FROM   ritual_memory
WHERE  ritual_name = ?
ORDER BY executed_at DESC
LIMIT  ?;
"""


class SQLiteAgentMemoryStore(AgentMemoryStore):
    def __init__(self, db_path: str = "~/.pm-agent/memory.db"):
        self._db_path = Path(db_path).expanduser()

    async def _ensure_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(_CREATE_TABLE)
            await db.execute(_CREATE_INDEX)
            await db.commit()

    async def write(self, entry: RitualMemoryEntry) -> None:
        await self._ensure_db()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                _INSERT,
                (
                    entry.id,
                    entry.ritual_name,
                    entry.sdlc_mode,
                    entry.executed_at.isoformat(),
                    entry.trigger,
                    entry.outcome_summary,
                    json.dumps(entry.tickets_affected),
                    json.dumps(entry.decisions),
                    entry.model_used,
                    int(entry.compression_occurred),
                ),
            )
            await db.commit()

    async def get_recent(
        self,
        ritual_name: str,
        limit: int = 5,
    ) -> list[RitualMemoryEntry]:
        await self._ensure_db()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(_SELECT_RECENT, (ritual_name, limit)) as cursor:
                rows = await cursor.fetchall()

        return [self._row_to_entry(row) for row in rows]

    async def get_context_injection(self, ritual_name: str) -> str:
        entries = await self.get_recent(ritual_name, limit=3)
        if not entries:
            return ""

        lines = [f"RECENT RITUAL HISTORY (last {len(entries)} {ritual_name} runs):"]
        for entry in entries:
            ts = entry.executed_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"- {ts} [{entry.trigger}]: {entry.outcome_summary}")

        return "\n".join(lines)

    @staticmethod
    def _row_to_entry(row: aiosqlite.Row) -> RitualMemoryEntry:
        return RitualMemoryEntry(
            id=row["id"],
            ritual_name=row["ritual_name"],
            sdlc_mode=row["sdlc_mode"],
            executed_at=datetime.fromisoformat(row["executed_at"]),
            trigger=row["trigger"],
            outcome_summary=row["outcome_summary"],
            tickets_affected=json.loads(row["tickets_affected"]),
            decisions=json.loads(row["decisions"]),
            model_used=row["model_used"],
            compression_occurred=bool(row["compression_occurred"]),
        )
