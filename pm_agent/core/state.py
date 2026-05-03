"""
LangGraph agent state definition.

Defined here in Phase 3 (needed by context management layer).
The full agent graph is wired in Phase 7.

Annotated list fields use operator.add as the LangGraph reducer so nodes
can return partial dicts and LangGraph appends rather than overwrites.
"""

import operator
from typing import Annotated, Any, Literal, Optional

from langchain_core.messages import BaseMessage

from pm_agent.adapters.ticket.models import Ticket, TeamMember


class PMAgentState(dict):
    """
    LangGraph agent state.

    Implemented as a TypedDict-compatible dict subclass so it can be used
    both as a LangGraph state schema (TypedDict-style) and manipulated with
    standard dict operations before Phase 7 wires the full graph.

    Fields with Annotated[list, operator.add] accumulate across graph nodes.
    """

    # Ritual identity
    ritual_name: str
    sdlc_mode: str
    trigger: Literal["cron", "prompt"]

    # Data
    tickets: Annotated[list[Ticket], operator.add]
    team: list[TeamMember]

    # LLM I/O
    messages: Annotated[list[BaseMessage], operator.add]
    llm_output: Optional[Any]

    # Approval / HITL
    approval_status: Optional[str]
    hitl_queue_id: Optional[str]

    # Context management (populated by Phase 3 layer)
    rolling_summary: Optional[str]
    context_budget_used_pct: float
    state_compressed: bool

    # Observability
    execution_trace: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]


def make_initial_state(
    ritual_name: str,
    sdlc_mode: str = "sdd",
    trigger: Literal["cron", "prompt"] = "prompt",
) -> PMAgentState:
    """Create a blank PMAgentState with safe defaults for all fields."""
    state: PMAgentState = PMAgentState(
        ritual_name=ritual_name,
        sdlc_mode=sdlc_mode,
        trigger=trigger,
        tickets=[],
        team=[],
        messages=[],
        llm_output=None,
        approval_status=None,
        hitl_queue_id=None,
        rolling_summary=None,
        context_budget_used_pct=0.0,
        state_compressed=False,
        execution_trace=[],
        errors=[],
    )
    return state
