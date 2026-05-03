"""
Summarization middleware.

Compresses bloated message lists into a rolling summary + tail window.
Always preserves:
  - All SystemMessages (they carry the ritual's core instructions)
  - The last `tail_window` messages (recent context for continuity)
The middle messages are replaced by a single summary HumanMessage.
"""

from typing import Optional

import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from pm_agent.config.models import ModelTierConfig

log = structlog.get_logger()

SUMMARIZATION_PROMPT = """You are a context compressor for a project management agent.
Summarize the following conversation history concisely, preserving:
- All decisions made
- All ticket IDs referenced and their current status
- All ritual outputs produced
- Any blockers or open questions raised
- Team member assignments mentioned

Be factual and terse. Output only the summary, no preamble.

Prior summary (if any):
{prior_summary}

Messages to compress:
{messages_to_compress}
"""


class CompressionResult(BaseModel):
    compressed_messages: list[BaseMessage]
    rolling_summary: str
    tokens_before: int  # message count of compressed portion (proxy for tokens)
    tokens_after: int   # always 1 — the summary message replaces all compressed msgs
    compression_ratio: float


class SummarizationMiddleware:
    def __init__(self, fast_llm: BaseChatModel, tail_window: int = 4):
        self.llm = fast_llm
        self.tail_window = tail_window

    async def compress(
        self,
        messages: list[BaseMessage],
        prior_summary: Optional[str],
        model_config: ModelTierConfig,
    ) -> CompressionResult:
        """
        Compress the message list by summarising everything except system messages
        and the tail window.

        Args:
            messages: Full message list from the current ritual invocation.
            prior_summary: Rolling summary from the previous compression (if any).
            model_config: Active model config (used for logging only at this layer).

        Returns:
            CompressionResult with compressed messages and updated rolling summary.
        """
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        tail = messages[-self.tail_window:] if len(messages) > self.tail_window else messages

        # Exclude system messages and tail from the messages to compress
        tail_set = set(id(m) for m in tail)
        system_set = set(id(m) for m in system_msgs)
        to_compress = [
            m for m in messages
            if id(m) not in system_set and id(m) not in tail_set
        ]

        if not to_compress:
            return CompressionResult(
                compressed_messages=messages,
                rolling_summary=prior_summary or "",
                tokens_before=0,
                tokens_after=0,
                compression_ratio=1.0,
            )

        prompt = SUMMARIZATION_PROMPT.format(
            prior_summary=prior_summary or "None",
            messages_to_compress="\n".join(
                f"[{m.__class__.__name__}]: {m.content}" for m in to_compress
            ),
        )

        summary_response = await self.llm.ainvoke(prompt)
        new_summary: str = str(summary_response.content)

        log.info(
            "context_compressed",
            msgs_compressed=len(to_compress),
            model=model_config.model,
        )

        compressed = (
            system_msgs
            + [HumanMessage(content=f"[CONTEXT SUMMARY]\n{new_summary}")]
            + tail
        )

        return CompressionResult(
            compressed_messages=compressed,
            rolling_summary=new_summary,
            tokens_before=len(to_compress),
            tokens_after=1,
            compression_ratio=1 / max(len(to_compress), 1),
        )
