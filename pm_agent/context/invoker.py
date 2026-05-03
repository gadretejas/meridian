"""
ContextAwareLLMInvoker — the single enforcement seam for all ritual LLM calls.

Every ritual calls this instead of llm.ainvoke() directly. It:
  1. Checks the context budget
  2. Compresses messages if the budget is over threshold
  3. Updates rolling_summary and context_budget_used_pct in state
  4. Invokes the LLM and returns (response, updated_state)
"""

import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from pm_agent.config.models import ModelTierConfig
from pm_agent.context.budget_watcher import ContextBudgetWatcher
from pm_agent.context.summarization import SummarizationMiddleware
from pm_agent.core.state import PMAgentState

log = structlog.get_logger()


class ContextAwareLLMInvoker:
    def __init__(
        self,
        watcher: ContextBudgetWatcher,
        summarizer: SummarizationMiddleware,
    ) -> None:
        self.watcher = watcher
        self.summarizer = summarizer

    async def invoke(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        model_config: ModelTierConfig,
        ritual_name: str,
        state: PMAgentState,
        ritual_overrides: dict = {},
    ) -> tuple[BaseMessage, PMAgentState]:
        """
        Invoke the LLM with automatic context compression if the budget is exceeded.

        Args:
            llm: BaseChatModel instance for this call (from get_llm).
            messages: Message list to send (may be compressed before sending).
            model_config: Resolved ModelTierConfig for the active model.
            ritual_name: Calling ritual name (for threshold and logging).
            state: Current PMAgentState (will be updated if compression fires).
            ritual_overrides: Loaded ritual_config.yaml dict.

        Returns:
            (response_message, updated_state) tuple.
        """
        budget = self.watcher.check(messages, model_config, ritual_name, ritual_overrides)

        if budget.should_compress:
            log.info(
                "context_compression_triggered",
                ritual=ritual_name,
                estimated_pct=round(budget.estimated_pct, 3),
                actual_pct=round(budget.actual_pct or budget.estimated_pct, 3),
                threshold=budget.threshold,
            )
            result = await self.summarizer.compress(
                messages,
                state.get("rolling_summary"),
                model_config,
            )
            messages = result.compressed_messages
            state = PMAgentState(
                **{
                    **state,
                    "rolling_summary": result.rolling_summary,
                    "context_budget_used_pct": budget.actual_pct or budget.estimated_pct,
                }
            )

        response = await llm.ainvoke(messages)
        return response, state
