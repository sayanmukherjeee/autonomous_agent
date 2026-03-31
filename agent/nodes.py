"""
LangGraph node functions.

Graph topology:
  agent_node  →  (routing)  →  human_approval_node  →  tools_node  → agent_node  → …
                           ↘  tools_node (no-approval tools)        ↗
                           ↘  END (when FINISHED)
"""

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from agent.state import AgentState
from agent.llm_factory import get_llm
from agent.prompts import get_system_prompt
from tools.file_tools import read_file, write_file, search_files, list_directory
from tools.terminal_tools import run_command
from tools.github_tools import create_branch, commit_and_push, create_pr, get_issue
from config.settings import settings

# ─────────────────────────────────────────────
# Tool registry
# ─────────────────────────────────────────────

ALL_TOOLS = [
    read_file,
    write_file,
    search_files,
    list_directory,
    run_command,
    create_branch,
    commit_and_push,
    create_pr,
    get_issue,
]

TOOLS_MAP = {t.name: t for t in ALL_TOOLS}

APPROVAL_REQUIRED: set = set(settings.require_approval_for)


# ─────────────────────────────────────────────
# Node: agent
# ─────────────────────────────────────────────

def agent_node(state: AgentState) -> AgentState:
    """Invoke the LLM (with tools bound) and decide what to do next."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    messages = list(state["messages"])

    # Prepend system prompt if not already present
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=get_system_prompt(str(settings.repo_path)))] + messages

    response: AIMessage = llm_with_tools.invoke(messages)

    # Append the AI response to the conversation
    new_messages = list(state["messages"]) + [response]

    if response.tool_calls:
        tool_call = response.tool_calls[0]          # handle one tool at a time
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]

        next_action = "human_approval" if tool_name in APPROVAL_REQUIRED else "tools"

        return {
            **state,
            "messages": new_messages,
            "next_action": next_action,
            "current_tool": tool_name,
            "tool_args": tool_args,
            "tool_call_id": tool_call_id,
            "human_decision": None,         # reset any previous decision
        }

    # No tool calls → check for FINISHED signal
    if "FINISHED" in response.content:
        return {**state, "messages": new_messages, "next_action": "finish"}

    # LLM replied with plain text (thinking out loud) → loop back
    return {**state, "messages": new_messages, "next_action": "agent"}


# ─────────────────────────────────────────────
# Node: tools  (executes the pending tool call)
# ─────────────────────────────────────────────

def tools_node(state: AgentState) -> AgentState:
    """Execute the pending tool and append a ToolMessage with the result."""
    tool_name = state["current_tool"]
    tool_args = state["tool_args"] or {}
    tool_call_id = state.get("tool_call_id", "call_unknown")

    tool_fn = TOOLS_MAP.get(tool_name)
    if tool_fn is None:
        result_content = f"ERROR: Tool '{tool_name}' not found in registry."
    else:
        try:
            result_content = tool_fn.invoke(tool_args)
        except Exception as exc:
            result_content = f"ERROR executing '{tool_name}': {exc}"

    tool_msg = ToolMessage(content=str(result_content), tool_call_id=tool_call_id)

    return {
        **state,
        "messages": list(state["messages"]) + [tool_msg],
        "next_action": "agent",
        "current_tool": None,
        "tool_args": None,
        "tool_call_id": None,
        "error": None,
    }


# ─────────────────────────────────────────────
# Node: human_approval  (stub — real I/O in CLI/API)
# ─────────────────────────────────────────────

def human_approval_node(state: AgentState) -> AgentState:
    """
    Pause point.  The CLI / API runner intercepts the graph here,
    asks the user y/n, then updates state["human_decision"] before
    the graph is allowed to continue.
    """
    # Just mark as waiting — the runner handles the actual prompt
    return {**state, "next_action": "waiting_for_human"}
