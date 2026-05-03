# Context Management Layer — Test Scenarios

Unit test coverage for `pm_agent/context/` (Phase 3).
All LLM and database calls are mocked or use temp SQLite files — no live API calls, no persistent side-effects.

Corresponding test files:
- `tests/unit/test_budget_watcher.py`
- `tests/unit/test_summarization.py`
- `tests/unit/test_state_compressor.py`
- `tests/unit/test_agent_memory.py`

---

## 1. `ContextBudgetWatcher` — `test_budget_watcher.py`

### 1a. Stage 1 — Character Proxy Early Exit

| # | Scenario | Expected |
|---|----------|----------|
| 1.1 | Estimated usage 20% | Stage 2 not called; `should_compress=False`, `actual_pct=None` |
| 1.2 | Estimated usage 74% (just below 75% trigger) | Stage 2 not called; early exit |
| 1.3 | Estimated usage 76% (just above 75% trigger) | Stage 2 fires; `actual_pct` populated |
| 1.4 | Any call | Returns `BudgetStatus` Pydantic model |

> **Why 75%?** The proxy is always an approximation. Waiting until 75% before calling the (potentially costly) token-count API means we never pay for Stage 2 unless we're genuinely close to the limit.

### 1b. Stage 2 — Compression Decision

| # | Scenario | Expected |
|---|----------|----------|
| 1.5 | Stage 2 actual = 80%, threshold = 85% | `should_compress=False` |
| 1.6 | Stage 2 actual = 85% (== threshold) | `should_compress=True` |
| 1.7 | Stage 2 actual = 95% (above threshold) | `should_compress=True` |

### 1c. Threshold Override

| # | Scenario | Expected |
|---|----------|----------|
| 1.8 | Ritual override sets `context_threshold=0.60`, actual=70% | `should_compress=True`, `threshold=0.60` |
| 1.9 | No override present | Global threshold from `config.yaml` used |

### 1d. Ollama — Stage 2 Skipped

| # | Scenario | Expected |
|---|----------|----------|
| 1.10 | Ollama provider, any message list | `get_llm` never called; proxy used as final value; `actual_pct` still populated |
| 1.11 | Ollama with `ollama_context_limit=4096` | `model_limit_tokens=4096` in BudgetStatus |

> **Why skip Stage 2 for Ollama?** `ChatOllama` does not implement `get_num_tokens_from_messages()`. Calling it raises `NotImplementedError`. The proxy estimate is used as the final value instead.

### 1e. BudgetStatus Fields

| # | Scenario | Expected |
|---|----------|----------|
| 1.12 | Gemini model | `model_limit_tokens=1_048_576` |
| 1.13 | Ollama llama3.2 | `model_limit_tokens=131_072` |
| 1.14 | Any call | `estimated_pct > 0` for non-empty message list |

---

## 2. `SummarizationMiddleware` — `test_summarization.py`

### 2a. Basic Compression

| # | Scenario | Expected |
|---|----------|----------|
| 2.1 | 6 messages, tail=2 | Returns `CompressionResult` |
| 2.2 | LLM returns specific text | `rolling_summary` matches LLM output |
| 2.3 | Compression fires | One `[CONTEXT SUMMARY]` HumanMessage injected into output |

### 2b. System Message Preservation

| # | Scenario | Expected |
|---|----------|----------|
| 2.4 | SystemMessage present in list | SystemMessage in compressed output |
| 2.5 | SystemMessage present | SystemMessage is first in output list |
| 2.6 | Two SystemMessages present | Both preserved in output |

### 2c. Tail Window Preservation

| # | Scenario | Expected |
|---|----------|----------|
| 2.7 | 8 messages, tail=3 | Last 3 messages present in output |
| 2.8 | Messages before tail | Not present directly in output (replaced by summary) |

### 2d. Edge Case — Short Message List

| # | Scenario | Expected |
|---|----------|----------|
| 2.9 | 3 messages, tail_window=4 (list shorter than window) | No compression; original messages returned unchanged; `compression_ratio=1.0`; LLM not called |
| 2.10 | Single message, tail_window=4 | Same — no compression, LLM not called |

> **Why this matters**: Without this guard, compressing a list shorter than tail_window would produce an empty `to_compress` list, and calling the LLM with an empty compression prompt would waste tokens and produce a nonsense summary.

### 2e. Rolling Summary Accumulation

| # | Scenario | Expected |
|---|----------|----------|
| 2.11 | Prior summary provided | Prior summary string included in LLM prompt |
| 2.12 | Two sequential compressions | Second `rolling_summary` reflects second LLM call output |

### 2f. CompressionResult Fields

| # | Scenario | Expected |
|---|----------|----------|
| 2.13 | Compression fires | `tokens_after=1` (one summary message replaces all compressed msgs) |
| 2.14 | 6 messages, tail=2 | `tokens_before=4` (4 messages were compressed) |

---

## 3. `compress_state` Node — `test_state_compressor.py`

### 3a. Ticket Compression

| # | Scenario | Expected |
|---|----------|----------|
| 3.1 | 10 tickets, threshold=50 | No compression; all `Ticket` objects; `state_compressed` not set |
| 3.2 | 51 tickets, threshold=50 | All converted to `TicketSummary` |
| 3.3 | Ticket summary fields | `id`, `title`, `status`, `priority` preserved |
| 3.4 | 51 tickets | `state_compressed=True` |
| 3.5 | 5 tickets | `state_compressed` not set to True |
| 3.6 | 60 tickets | Length preserved (60 summaries) |

### 3b. Trace Compression

| # | Scenario | Expected |
|---|----------|----------|
| 3.7 | 50 trace entries, threshold=100 | No trimming; `state_compressed` not set |
| 3.8 | 101 trace entries, threshold=100 | Trimmed to `trace_keep_last (20) + 1` = 21 entries |
| 3.9 | 101 trace entries | First entry starts with `[TRACE COMPRESSED:` |
| 3.10 | 110 trace entries, keep_last=20 | Kept entries are steps 90–109 (last 20) |
| 3.11 | 101 trace entries | `state_compressed=True` |

### 3c. Both Thresholds Exceeded

| # | Scenario | Expected |
|---|----------|----------|
| 3.12 | 55 tickets + 105 trace entries | Both compressed; `state_compressed=True` |

### 3d. Return Type and Field Preservation

| # | Scenario | Expected |
|---|----------|----------|
| 3.13 | Any state | Returns `dict` (LangGraph compatible) |
| 3.14 | State with custom `sdlc_mode` and `trigger` | Those fields unchanged in output |

---

## 4. `SQLiteAgentMemoryStore` — `test_agent_memory.py`

### 4a. Write + Read Round-Trip

| # | Scenario | Expected |
|---|----------|----------|
| 4.1 | Write one entry, read back | Entry retrieved with correct `outcome_summary` |
| 4.2 | Write one entry | `id` is preserved exactly |
| 4.3 | Entry with `tickets_affected=["#1","#5","#12"]` | List round-trips correctly (JSON serialisation) |
| 4.4 | Entry with `decisions` list | List round-trips correctly |
| 4.5 | Entry with `compression_occurred=True` | Bool preserved through INTEGER column |
| 4.6 | Entry with empty lists | Empty lists preserved (not None) |

### 4b. Ordering — Newest First

| # | Scenario | Expected |
|---|----------|----------|
| 4.7 | 3 entries with distinct timestamps | Returned newest-first |
| 4.8 | 5 entries, `limit=3` | Only 3 returned |

### 4c. Ritual Name Isolation

| # | Scenario | Expected |
|---|----------|----------|
| 4.9 | Entries for two different rituals | `get_recent("standup_agenda")` only returns standup entries |
| 4.10 | Query unknown ritual name | Returns empty list |

### 4d. `get_context_injection` Format

| # | Scenario | Expected |
|---|----------|----------|
| 4.11 | No entries in DB | Returns `""` |
| 4.12 | One entry | Output contains ritual name |
| 4.13 | One entry | Output contains `outcome_summary` |
| 4.14 | One entry with `trigger="cron"` | Output contains `[cron]` |
| 4.15 | 5 entries | Only 3 bullet lines in output |
| 4.16 | Any entries | First line starts with `RECENT RITUAL HISTORY` |

---

## Coverage Summary

| Module | Test File | Scenarios |
|--------|-----------|-----------|
| `context/limits.py` | Covered via `budget_watcher` tests (scenarios 1.12–1.13) | 3 |
| `context/budget_watcher.py` | `test_budget_watcher.py` | 14 |
| `context/summarization.py` | `test_summarization.py` | 14 |
| `context/state_compressor.py` | `test_state_compressor.py` | 14 |
| `context/memory/sqlite.py` | `test_agent_memory.py` | 16 |

**Total: 61 scenarios**

---

## What Is NOT Tested Here

| Scenario | Reason | Where it's tested |
|----------|--------|-------------------|
| `ContextAwareLLMInvoker` end-to-end | Wires together all other components — covered by integration tests | Future integration tests |
| Live LLM compression call | Requires real API keys | Manual verification / live integration tests |
| Concurrent SQLite writes | Not a Phase 3 concern; rituals run sequentially by design | Deferred to Phase 9 (scheduler) |
| DB migration / schema changes | Schema is fixed for Phase 3; migrations added in later phases | Phase 9+ |
| Ollama `get_num_tokens_from_messages` fallback via `NotImplementedError` | Internal helper; covered indirectly by Ollama tests 1.10–1.11 | Implicit |
