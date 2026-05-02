"""LLM provider router — public surface."""

from pm_agent.adapters.llm.factory import get_llm
from pm_agent.adapters.llm.resolver import resolve_model_config
from pm_agent.adapters.llm.structured import get_structured_llm

__all__ = ["get_llm", "resolve_model_config", "get_structured_llm"]
