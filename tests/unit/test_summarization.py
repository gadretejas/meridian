"""
Unit tests for SummarizationMiddleware (Phase 3, Task 3.3).
LLM calls are mocked — no live API calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from pm_agent.config.models import ModelTierConfig
from pm_agent.context.summarization import CompressionResult, SummarizationMiddleware


def _tier(provider: str = "gemini", model: str = "models/gemini-2.0-flash") -> ModelTierConfig:
    return ModelTierConfig(provider=provider, model=model, temperature=0.3, max_tokens=1024)


def _mock_llm(summary_text: str = "Summary of prior work.") -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=summary_text))
    return llm


@pytest.fixture
def model_config() -> ModelTierConfig:
    return _tier()


# ---------------------------------------------------------------------------
# Basic compression
# ---------------------------------------------------------------------------

class TestBasicCompression:
    @pytest.mark.asyncio
    async def test_returns_compression_result(self, model_config):
        llm = _mock_llm()
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(6)]
        result = await middleware.compress(msgs, None, model_config)
        assert isinstance(result, CompressionResult)

    @pytest.mark.asyncio
    async def test_rolling_summary_contains_llm_output(self, model_config):
        llm = _mock_llm("Tickets #1 and #2 discussed.")
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(6)]
        result = await middleware.compress(msgs, None, model_config)
        assert result.rolling_summary == "Tickets #1 and #2 discussed."

    @pytest.mark.asyncio
    async def test_summary_message_injected_into_compressed_messages(self, model_config):
        llm = _mock_llm("Compressed summary here.")
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(6)]
        result = await middleware.compress(msgs, None, model_config)
        summary_msgs = [m for m in result.compressed_messages if "[CONTEXT SUMMARY]" in str(m.content)]
        assert len(summary_msgs) == 1


# ---------------------------------------------------------------------------
# System message preservation
# ---------------------------------------------------------------------------

class TestSystemMessagePreservation:
    @pytest.mark.asyncio
    async def test_system_message_always_in_output(self, model_config):
        llm = _mock_llm()
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        sys_msg = SystemMessage(content="You are a PM agent.")
        msgs = [sys_msg] + [HumanMessage(content=f"msg {i}") for i in range(5)]
        result = await middleware.compress(msgs, None, model_config)
        assert sys_msg in result.compressed_messages

    @pytest.mark.asyncio
    async def test_system_message_is_first(self, model_config):
        llm = _mock_llm()
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        sys_msg = SystemMessage(content="System.")
        msgs = [sys_msg] + [HumanMessage(content=f"msg {i}") for i in range(5)]
        result = await middleware.compress(msgs, None, model_config)
        assert result.compressed_messages[0] is sys_msg

    @pytest.mark.asyncio
    async def test_multiple_system_messages_all_preserved(self, model_config):
        llm = _mock_llm()
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        sys1 = SystemMessage(content="Role prompt.")
        sys2 = SystemMessage(content="SDLC context.")
        msgs = [sys1, sys2] + [HumanMessage(content=f"msg {i}") for i in range(5)]
        result = await middleware.compress(msgs, None, model_config)
        output_sys = [m for m in result.compressed_messages if isinstance(m, SystemMessage)]
        assert sys1 in output_sys
        assert sys2 in output_sys


# ---------------------------------------------------------------------------
# Tail window preservation
# ---------------------------------------------------------------------------

class TestTailWindowPreservation:
    @pytest.mark.asyncio
    async def test_last_n_messages_preserved(self, model_config):
        llm = _mock_llm()
        tail_window = 3
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=tail_window)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(8)]
        tail = msgs[-tail_window:]
        result = await middleware.compress(msgs, None, model_config)
        for t in tail:
            assert t in result.compressed_messages

    @pytest.mark.asyncio
    async def test_messages_before_tail_not_in_output(self, model_config):
        llm = _mock_llm()
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(6)]
        result = await middleware.compress(msgs, None, model_config)
        # msgs 0-3 should not appear directly (replaced by summary)
        for msg in msgs[:-2]:
            assert msg not in result.compressed_messages


# ---------------------------------------------------------------------------
# Edge case — message list shorter than tail_window
# ---------------------------------------------------------------------------

class TestShortMessageList:
    @pytest.mark.asyncio
    async def test_no_compression_when_nothing_to_compress(self, model_config):
        """If all messages fit inside the tail window, nothing is compressed."""
        llm = _mock_llm()
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=4)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(3)]
        result = await middleware.compress(msgs, None, model_config)
        assert result.compressed_messages == msgs
        assert result.compression_ratio == 1.0
        llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_message_list_not_compressed(self, model_config):
        llm = _mock_llm()
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=4)
        msgs = [HumanMessage(content="only message")]
        result = await middleware.compress(msgs, None, model_config)
        assert result.compressed_messages == msgs
        llm.ainvoke.assert_not_called()


# ---------------------------------------------------------------------------
# Rolling summary accumulation
# ---------------------------------------------------------------------------

class TestRollingSummaryAccumulation:
    @pytest.mark.asyncio
    async def test_prior_summary_passed_to_prompt(self, model_config):
        llm = _mock_llm("Updated summary.")
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(6)]
        prior = "Previous run: #5 was closed."
        result = await middleware.compress(msgs, prior, model_config)
        # prior summary should have been included in the prompt
        call_prompt = str(llm.ainvoke.call_args)
        assert "Previous run: #5 was closed." in call_prompt

    @pytest.mark.asyncio
    async def test_two_compressions_produce_distinct_summaries(self, model_config):
        llm = _mock_llm("First summary.")
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(6)]
        first = await middleware.compress(msgs, None, model_config)

        llm.ainvoke = AsyncMock(return_value=AIMessage(content="Second summary."))
        second = await middleware.compress(msgs, first.rolling_summary, model_config)
        assert second.rolling_summary == "Second summary."


# ---------------------------------------------------------------------------
# CompressionResult fields
# ---------------------------------------------------------------------------

class TestCompressionResultFields:
    @pytest.mark.asyncio
    async def test_tokens_after_is_one_when_compression_occurs(self, model_config):
        llm = _mock_llm()
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=2)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(6)]
        result = await middleware.compress(msgs, None, model_config)
        assert result.tokens_after == 1

    @pytest.mark.asyncio
    async def test_tokens_before_equals_compressed_message_count(self, model_config):
        llm = _mock_llm()
        tail_window = 2
        middleware = SummarizationMiddleware(fast_llm=llm, tail_window=tail_window)
        msgs = [HumanMessage(content=f"msg {i}") for i in range(6)]
        result = await middleware.compress(msgs, None, model_config)
        # 6 messages, tail=2 → 4 compressed
        assert result.tokens_before == 4
