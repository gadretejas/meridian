"""
Unit tests for ContextBudgetWatcher (Phase 3, Task 3.2).
All LLM API calls are mocked — no live provider calls.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

import math

from pm_agent.config.models import ModelTierConfig
from pm_agent.context.budget_watcher import (
    _CHARS_PER_TOKEN,
    _STAGE1_PROXY_THRESHOLD,
    BudgetStatus,
    ContextBudgetWatcher,
)


def _tier(provider: str, model: str, **kwargs) -> ModelTierConfig:
    return ModelTierConfig(provider=provider, model=model, temperature=0.3, max_tokens=1024, **kwargs)


def _messages_with_chars(total_chars: int) -> list:
    """Build a single HumanMessage whose content is exactly total_chars long."""
    return [HumanMessage(content="x" * total_chars)]


@pytest.fixture
def watcher() -> ContextBudgetWatcher:
    return ContextBudgetWatcher()


@pytest.fixture
def gemini_config() -> ModelTierConfig:
    return _tier("gemini", "models/gemini-2.0-flash")


@pytest.fixture
def ollama_config() -> ModelTierConfig:
    return _tier("ollama", "llama3.2")


# ---------------------------------------------------------------------------
# Stage 1 — character proxy early exit
# ---------------------------------------------------------------------------

class TestStage1ProxyEarlyExit:
    def test_exits_early_well_below_threshold(self, watcher, gemini_config):
        """20% estimated usage — Stage 2 never fires."""
        limit = 1_048_576
        chars = int(limit * 0.20 * _CHARS_PER_TOKEN)
        msgs = _messages_with_chars(chars)
        with patch.object(watcher, "_count_tokens_via_api") as mock_stage2:
            result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        mock_stage2.assert_not_called()
        assert result.should_compress is False
        assert result.actual_pct is None

    def test_exits_early_just_below_proxy_threshold(self, watcher, gemini_config):
        """74% estimated — stays below 75% stage-1 trigger, Stage 2 skipped."""
        limit = 1_048_576
        chars = int(limit * 0.74 * _CHARS_PER_TOKEN)
        msgs = _messages_with_chars(chars)
        with patch.object(watcher, "_count_tokens_via_api") as mock_stage2:
            result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        mock_stage2.assert_not_called()
        assert result.should_compress is False

    def test_stage2_fires_at_proxy_threshold(self, watcher, gemini_config):
        """76% estimated — crosses 75% stage-1 trigger, Stage 2 must run."""
        limit = 1_048_576
        chars = int(limit * 0.76 * _CHARS_PER_TOKEN)
        msgs = _messages_with_chars(chars)
        with patch.object(watcher, "_count_tokens_via_api", return_value=int(limit * 0.50)) as mock_stage2:
            result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        mock_stage2.assert_called_once()
        assert result.actual_pct is not None

    def test_returns_budget_status_model(self, watcher, gemini_config):
        msgs = _messages_with_chars(100)
        result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        assert isinstance(result, BudgetStatus)


# ---------------------------------------------------------------------------
# Stage 2 — compression decision
# ---------------------------------------------------------------------------

class TestStage2CompressionDecision:
    def test_no_compression_when_actual_below_threshold(self, watcher, gemini_config):
        """Stage 2 actual pct < 85% — should_compress False."""
        limit = 1_048_576
        chars = int(limit * 0.76 * _CHARS_PER_TOKEN)
        msgs = _messages_with_chars(chars)
        actual_tokens = int(limit * 0.80)  # 80%, below 85% default threshold
        with patch.object(watcher, "_count_tokens_via_api", return_value=actual_tokens):
            result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        assert result.should_compress is False
        assert result.actual_pct == pytest.approx(0.80, rel=0.01)

    def test_compression_triggered_at_threshold(self, watcher, gemini_config):
        """Actual pct >= 85% (the threshold) — should_compress True."""
        limit = 1_048_576
        chars = int(limit * 0.76 * _CHARS_PER_TOKEN)
        msgs = _messages_with_chars(chars)
        actual_tokens = math.ceil(limit * 0.85)  # ceil ensures actual_pct >= threshold exactly
        with patch.object(watcher, "_count_tokens_via_api", return_value=actual_tokens):
            result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        assert result.should_compress is True

    def test_compression_triggered_above_threshold(self, watcher, gemini_config):
        """Actual pct 95% — should_compress True."""
        limit = 1_048_576
        chars = int(limit * 0.76 * _CHARS_PER_TOKEN)
        msgs = _messages_with_chars(chars)
        actual_tokens = int(limit * 0.95)
        with patch.object(watcher, "_count_tokens_via_api", return_value=actual_tokens):
            result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        assert result.should_compress is True


# ---------------------------------------------------------------------------
# Threshold override
# ---------------------------------------------------------------------------

class TestThresholdOverride:
    def test_ritual_threshold_override_respected(self, watcher, gemini_config):
        """Per-ritual context_threshold overrides the global 0.85."""
        limit = 1_048_576
        chars = int(limit * 0.76 * _CHARS_PER_TOKEN)
        msgs = _messages_with_chars(chars)
        actual_tokens = int(limit * 0.70)  # 70%, above custom threshold of 0.60
        ritual_overrides = {"standup_agenda": {"context_threshold": 0.60}}
        with patch.object(watcher, "_count_tokens_via_api", return_value=actual_tokens):
            result = watcher.check(msgs, gemini_config, "standup_agenda", ritual_overrides)
        assert result.should_compress is True
        assert result.threshold == 0.60

    def test_global_threshold_used_when_no_override(self, watcher, gemini_config):
        from pm_agent.config.loader import load_config
        global_threshold = load_config().context_management.threshold
        limit = 1_048_576
        chars = int(limit * 0.76 * _CHARS_PER_TOKEN)
        msgs = _messages_with_chars(chars)
        with patch.object(watcher, "_count_tokens_via_api", return_value=10):
            result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        assert result.threshold == global_threshold


# ---------------------------------------------------------------------------
# Ollama — Stage 2 skipped
# ---------------------------------------------------------------------------

class TestOllamaSkipsStage2:
    def test_ollama_never_calls_provider_token_count(self, watcher, ollama_config):
        """Ollama has no token-count API; Stage 2 must use proxy only."""
        limit = 131_072
        chars = int(limit * 0.80 * _CHARS_PER_TOKEN)
        msgs = _messages_with_chars(chars)
        with patch("pm_agent.context.budget_watcher.get_llm") as mock_get_llm:
            result = watcher.check(msgs, ollama_config, "standup_agenda", {})
        mock_get_llm.assert_not_called()
        # actual_pct is still populated (proxy value used as final)
        assert result.actual_pct is not None

    def test_ollama_context_limit_override_used(self, watcher):
        custom_config = _tier("ollama", "llama3.2", ollama_context_limit=4096)
        # With 4096 limit and 3500-char message, estimated ~ 875 tokens = ~21% — Stage 2 skip
        msgs = _messages_with_chars(3500)
        with patch.object(watcher, "_count_tokens_via_api") as mock_stage2:
            result = watcher.check(msgs, custom_config, "standup_agenda", {})
        mock_stage2.assert_not_called()
        assert result.model_limit_tokens == 4096


# ---------------------------------------------------------------------------
# BudgetStatus fields
# ---------------------------------------------------------------------------

class TestBudgetStatusFields:
    def test_model_limit_tokens_correct_for_gemini(self, watcher, gemini_config):
        msgs = _messages_with_chars(100)
        result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        assert result.model_limit_tokens == 1_048_576

    def test_model_limit_tokens_correct_for_ollama(self, watcher, ollama_config):
        msgs = _messages_with_chars(100)
        result = watcher.check(msgs, ollama_config, "standup_agenda", {})
        assert result.model_limit_tokens == 131_072

    def test_estimated_pct_is_always_populated(self, watcher, gemini_config):
        msgs = _messages_with_chars(50)
        result = watcher.check(msgs, gemini_config, "standup_agenda", {})
        assert result.estimated_pct > 0
