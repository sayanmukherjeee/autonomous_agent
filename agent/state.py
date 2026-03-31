"""
AgentState — the single mutable object that flows through LangGraph nodes.
"""

from typing import Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    # Full conversation history (HumanMessage, AIMessage, ToolMessage, SystemMessage)
    messages: List[BaseMessage]

    # Routing signal set by each node
    next_action: Literal["agent", "tools", "human_approval", "waiting_for_human", "finish"]

    # The tool the agent decided to call (populated by agent_node)
    current_tool: Optional[str]

    # Arguments for the pending tool call
    tool_args: Optional[Dict[str, Any]]

    # The LangChain tool_call_id for the pending call (needed for ToolMessage)
    tool_call_id: Optional[str]

    # Set by CLI/API after asking the user
    human_decision: Optional[Literal["approved", "rejected"]]

    # Scratch-pad for multi-step reasoning (not used by graph routing, just for visibility)
    intermediate_steps: List[Any]

    # Last error message (surfaced to agent so it can self-correct)
    error: Optional[str]
