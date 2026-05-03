"""Context management layer — public surface."""

from pm_agent.context.budget_watcher import BudgetStatus, ContextBudgetWatcher
from pm_agent.context.invoker import ContextAwareLLMInvoker
from pm_agent.context.limits import MODEL_CONTEXT_LIMITS, get_context_limit
from pm_agent.context.state_compressor import compress_state
from pm_agent.context.summarization import CompressionResult, SummarizationMiddleware

__all__ = [
    "BudgetStatus",
    "ContextBudgetWatcher",
    "ContextAwareLLMInvoker",
    "MODEL_CONTEXT_LIMITS",
    "get_context_limit",
    "compress_state",
    "CompressionResult",
    "SummarizationMiddleware",
]
