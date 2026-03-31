"""
Smoke-tests for the LangGraph graph build and state routing.
Run:  python -m pytest tests/test_graph.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage


def _make_state(next_action="agent", current_tool=None, tool_args=None, human_decision=None):
    return {
        "messages": [HumanMessage(content="test")],
        "next_action": next_action,
        "current_tool": current_tool,
        "tool_args": tool_args or {},
        "tool_call_id": "call_test",
        "human_decision": human_decision,
        "intermediate_steps": [],
        "error": None,
    }


def test_graph_compiles():
    """Graph should compile without errors."""
    from agent.graph import build_graph
    g = build_graph()
    assert g is not None


def test_route_after_agent_to_tools():
    from agent.graph import route_after_agent
    state = _make_state(next_action="tools")
    assert route_after_agent(state) == "tools"


def test_route_after_agent_to_approval():
    from agent.graph import route_after_agent
    state = _make_state(next_action="human_approval")
    assert route_after_agent(state) == "human_approval"


def test_route_after_agent_finish():
    from agent.graph import route_after_agent
    from langgraph.graph import END
    state = _make_state(next_action="finish")
    assert route_after_agent(state) == END


def test_route_after_human_approved():
    from agent.graph import route_after_human
    state = _make_state(next_action="waiting_for_human", human_decision="approved", current_tool="write_file")
    assert route_after_human(state) == "tools"


def test_route_after_human_rejected():
    from agent.graph import route_after_human
    state = _make_state(next_action="waiting_for_human", human_decision="rejected", current_tool="write_file")
    result = route_after_human(state)
    assert result == "agent"
