"""
Interactive CLI for the Autonomous Code Agent.

Usage:
    python run_cli.py

The CLI drives the LangGraph manually step-by-step so it can intercept
human_approval nodes without needing LangGraph checkpointing.
"""

import sys
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from agent.graph import build_graph
from agent.state import AgentState
from config.settings import settings


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

BANNER = """\
╔══════════════════════════════════════════════╗
║    Autonomous Code Agent  (free LLM edition) ║
╚══════════════════════════════════════════════╝
Type your task and press Enter.
Commands:  /exit   /repo <path>   /status   /help
"""

HELP_TEXT = """\
Available commands:
  /exit              Quit the agent
  /repo <path>       Change the working repository path
  /status            Show current LLM provider and repo path
  /help              Show this help message
  
  (any other input)  Send task to the agent
"""


def _print_sep(char="─", width=52):
    print(char * width)


def _ask_approval(tool_name: str, tool_args: dict) -> bool:
    """Ask the user y/n for a pending tool call. Returns True if approved."""
    _print_sep("─")
    print(f"⚠️   APPROVAL REQUIRED")
    print(f"    Tool  : {tool_name}")
    print(f"    Args  :")
    for k, v in tool_args.items():
        val_str = str(v)
        if len(val_str) > 200:
            val_str = val_str[:200] + "…"
        print(f"      {k}: {val_str}")
    _print_sep("─")
    while True:
        answer = input("    Approve? [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("    Please enter 'y' or 'n'.")


def _run_agent_for_task(task: str) -> None:
    """Run the graph for a single user task, handling approvals interactively."""
    graph = build_graph()

    state: AgentState = {
        "messages": [HumanMessage(content=task)],
        "next_action": "agent",
        "current_tool": None,
        "tool_args": None,
        "tool_call_id": None,
        "human_decision": None,
        "intermediate_steps": [],
        "error": None,
    }

    max_iterations = 50
    iteration = 0

    while state["next_action"] != "finish" and iteration < max_iterations:
        iteration += 1

        # ── Run the graph until it hits a human_approval or finishes ──
        # We invoke single nodes manually based on next_action.

        action = state["next_action"]

        if action == "agent":
            print("\n🤖 Agent is thinking…")
            from agent.nodes import agent_node
            state = agent_node(state)

            # Print last AI message
            last = state["messages"][-1]
            if isinstance(last, AIMessage) and last.content:
                _print_sep()
                print(f"Agent:\n{last.content}")

        elif action == "tools":
            # Execute the tool directly (no approval needed for this tool)
            from agent.nodes import tools_node
            print(f"\n🔧 Running tool: {state['current_tool']}…")
            state = tools_node(state)

            last = state["messages"][-1]
            if isinstance(last, ToolMessage):
                result_preview = last.content[:500]
                if len(last.content) > 500:
                    result_preview += "\n…(truncated)"
                print(f"Tool result:\n{result_preview}")

        elif action in ("human_approval", "waiting_for_human"):
            # Ask the user
            approved = _ask_approval(
                state["current_tool"] or "unknown",
                state["tool_args"] or {},
            )
            state["human_decision"] = "approved" if approved else "rejected"

            if approved:
                print(f"✅ Approved. Executing '{state['current_tool']}'…")
                from agent.nodes import tools_node
                state = tools_node(state)
                last = state["messages"][-1]
                if isinstance(last, ToolMessage):
                    result_preview = last.content[:500]
                    if len(last.content) > 500:
                        result_preview += "\n…(truncated)"
                    print(f"Tool result:\n{result_preview}")
            else:
                print(f"❌ Rejected. Informing agent…")
                # Inject a rejection ToolMessage so the LLM can re-plan
                from langchain_core.messages import ToolMessage as TM
                rejection = TM(
                    content=(
                        f"The user rejected the call to '{state['current_tool']}'.\n"
                        "Please suggest an alternative or ask the user what to do next."
                    ),
                    tool_call_id=state.get("tool_call_id", "rejected"),
                )
                state["messages"].append(rejection)
                state["current_tool"] = None
                state["tool_args"] = None
                state["tool_call_id"] = None
                state["human_decision"] = None
                state["next_action"] = "agent"

        elif action == "finish":
            break

        else:
            # Shouldn't normally happen
            print(f"⚠️  Unexpected next_action='{action}'. Resetting to 'agent'.")
            state["next_action"] = "agent"

    if iteration >= max_iterations:
        print("\n⚠️  Reached maximum iteration limit (50). Stopping.")
    else:
        print("\n✅ Task complete.")


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def run_cli() -> None:
    print(BANNER)
    print(f"LLM provider : {settings.llm_provider}  ({settings.ollama_model if settings.llm_provider == 'ollama' else settings.gemini_model})")
    print(f"Repo path    : {settings.repo_path.resolve()}")
    _print_sep()

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            sys.exit(0)

        if not user_input:
            continue

        # ── Built-in commands ──
        if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
            print("Goodbye!")
            sys.exit(0)

        if user_input.lower() == "/help":
            print(HELP_TEXT)
            continue

        if user_input.lower() == "/status":
            print(f"LLM provider : {settings.llm_provider}")
            if settings.llm_provider == "ollama":
                print(f"Ollama model : {settings.ollama_model}")
                print(f"Ollama URL   : {settings.ollama_base_url}")
            else:
                print(f"Gemini model : {settings.gemini_model}")
            print(f"Repo path    : {settings.repo_path.resolve()}")
            print(f"GitHub token : {'set ✅' if settings.github_token and not settings.github_token.startswith('your_') else 'NOT set ❌'}")
            continue

        if user_input.lower().startswith("/repo "):
            new_path = user_input[6:].strip()
            p = Path(new_path)
            if p.exists() and p.is_dir():
                settings.repo_path = p.resolve()
                print(f"Repo path changed to: {settings.repo_path}")
            else:
                print(f"❌ Path not found or not a directory: {new_path}")
            continue

        # ── Agent task ──
        try:
            _run_agent_for_task(user_input)
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user.")
        except Exception as exc:
            print(f"\n❌ Unexpected error: {exc}")
            print("Check agent.log for details.")
            import traceback, logging
            logging.getLogger(__name__).error(traceback.format_exc())
