"""
Context budget watcher.

Two-stage check to avoid unnecessary token-counting API calls:
  Stage 1 — character proxy (always runs, zero cost).
            Exits early if estimated usage < 75% of context limit.
  Stage 2 — actual token count via provider API.
            Runs only when Stage 1 estimate is >= 75%.
            Ollama skips Stage 2 (ChatOllama has no token-count API);
            the Stage 1 proxy is used as the final value.
"""

from typing import Optional

import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from pm_agent.adapters.llm.factory import get_llm
from pm_agent.config.models import ModelTierConfig
from pm_agent.context.limits import get_context_limit

log = structlog.get_logger()

_STAGE1_PROXY_THRESHOLD = 0.75  # Below this, skip Stage 2 entirely
_CHARS_PER_TOKEN = 4             # Conservative character-to-token proxy


class BudgetStatus(BaseModel):
    estimated_pct: float
    actual_pct: Optional[float] = None
    threshold: float
    should_compress: bool
    model_limit_tokens: int


class ContextBudgetWatcher:
    def check(
        self,
        messages: list[BaseMessage],
        model_config: ModelTierConfig,
        ritual_name: str,
        ritual_overrides: dict,
    ) -> BudgetStatus:
        """
        Check whether the message list is approaching the model's context limit.

        Args:
            messages: Current message list for the active ritual invocation.
            model_config: Resolved ModelTierConfig for the active LLM.
            ritual_name: Name of the calling ritual (for per-ritual threshold overrides).
            ritual_overrides: Loaded ritual_config.yaml dict.

        Returns:
            BudgetStatus with estimated/actual usage and whether compression should fire.
        """
        limit = get_context_limit(model_config)
        threshold = self._get_threshold(ritual_name, ritual_overrides)

        # Stage 1: character proxy — zero API cost
        total_chars = sum(len(str(m.content)) for m in messages)
        estimated_tokens = total_chars / _CHARS_PER_TOKEN
        estimated_pct = estimated_tokens / limit

        if estimated_pct < _STAGE1_PROXY_THRESHOLD:
            return BudgetStatus(
                estimated_pct=estimated_pct,
                threshold=threshold,
                should_compress=False,
                model_limit_tokens=limit,
            )

        # Stage 2: actual token count via provider API
        actual_tokens = self._count_tokens_via_api(messages, model_config)
        actual_pct = actual_tokens / limit

        log.debug(
            "context_budget_check",
            ritual=ritual_name,
            estimated_pct=round(estimated_pct, 3),
            actual_pct=round(actual_pct, 3),
            threshold=threshold,
        )

        return BudgetStatus(
            estimated_pct=estimated_pct,
            actual_pct=actual_pct,
            threshold=threshold,
            should_compress=actual_pct >= threshold,
            model_limit_tokens=limit,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_threshold(self, ritual_name: str, ritual_overrides: dict) -> float:
        """
        Return the compression threshold for this ritual.
        Ritual-level context_threshold overrides the global config value.
        """
        from pm_agent.config.loader import load_config
        global_threshold = load_config().context_management.threshold
        return ritual_overrides.get(ritual_name, {}).get("context_threshold", global_threshold)

    def _count_tokens_via_api(
        self,
        messages: list[BaseMessage],
        model_config: ModelTierConfig,
    ) -> int:
        """
        Count tokens using the provider's own token-counting method.

        Falls back to the character proxy for Ollama (ChatOllama does not
        implement get_num_tokens_from_messages) and for any provider that
        raises NotImplementedError.
        """
        if model_config.provider == "ollama":
            # Ollama has no token-count API; use proxy as final value
            total_chars = sum(len(str(m.content)) for m in messages)
            return int(total_chars / _CHARS_PER_TOKEN)

        try:
            llm: BaseChatModel = get_llm(model_config)
            return llm.get_num_tokens_from_messages(messages)
        except (NotImplementedError, AttributeError):
            total_chars = sum(len(str(m.content)) for m in messages)
            return int(total_chars / _CHARS_PER_TOKEN)
