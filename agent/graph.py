"""
LangGraph workflow definition.

Graph edges
───────────
agent  ──(needs approval)──▶  human_approval  ──(approved)──▶  tools  ──▶  agent
       ──(no approval)──────▶  tools           ──────────────────────────▶  agent
       ──(FINISHED)──────────▶  END
       ──(loop/text only)────▶  agent

human_approval ──(rejected)──▶  agent   (with a rejection ToolMessage)
"""

from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import agent_node, tools_node, human_approval_node
from langchain_core.messages import ToolMessage


# ─────────────────────────────────────────────
# Routing functions
# ─────────────────────────────────────────────

def route_after_agent(state: AgentState) -> str:
    action = state.get("next_action", "agent")
    if action == "tools":
        return "tools"
    if action == "human_approval":
        return "human_approval"
    if action == "finish":
        return END
    return "agent"   # loop (plain text response from LLM)


def route_after_human(state: AgentState) -> str:
    decision = state.get("human_decision")
    if decision == "approved":
        return "tools"
    # Rejected — inject a ToolMessage so the LLM knows and can re-plan
    rejection_msg = ToolMessage(
        content=(
            f"The user rejected the call to '{state.get('current_tool')}'.\n"
            "Please re-think your approach and propose an alternative or ask the user what to do."
        ),
        tool_call_id=state.get("tool_call_id", "rejected"),
    )
    state["messages"].append(rejection_msg)
    state["current_tool"] = None
    state["tool_args"] = None
    state["tool_call_id"] = None
    return "agent"


# ─────────────────────────────────────────────
# Build & compile
# ─────────────────────────────────────────────

def build_graph():
    wf = StateGraph(AgentState)

    wf.add_node("agent", agent_node)
    wf.add_node("tools", tools_node)
    wf.add_node("human_approval", human_approval_node)

    wf.set_entry_point("agent")

    wf.add_conditional_edges("agent", route_after_agent)
    wf.add_edge("tools", "agent")
    wf.add_conditional_edges("human_approval", route_after_human)

    return wf.compile()
