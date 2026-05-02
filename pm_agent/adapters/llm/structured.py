"""
Structured output helper.

Wraps llm.with_structured_output() with include_raw=True so callers can
inspect the raw LLM response when Pydantic parsing fails.
"""

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel


def get_structured_llm(
    llm: BaseChatModel,
    schema: type[BaseModel],
    max_retries: int = 3,
) -> Runnable:
    """
    Return a Runnable that enforces structured Pydantic output from an LLM.

    include_raw=True surfaces the raw model message alongside the parsed object,
    which is essential for debugging parse failures.

    Retry logic lives in the calling ritual (via tenacity) rather than here,
    keeping this layer thin and testable. The max_retries parameter is stored
    on the returned runnable as metadata for callers that need it.

    Args:
        llm: A BaseChatModel instance (from get_llm).
        schema: The Pydantic BaseModel class that defines the expected output shape.
        max_retries: Hint for callers — how many retries to attempt on parse failure.

    Returns:
        A LangChain Runnable whose output is {"raw": AIMessage, "parsed": schema | None, "parsing_error": ...}.
    """
    runnable: Any = llm.with_structured_output(schema, include_raw=True)
    runnable.max_retries = max_retries  # type: ignore[attr-defined]
    return runnable  # type: ignore[return-value]
