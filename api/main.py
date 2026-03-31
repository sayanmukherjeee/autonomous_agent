"""
FastAPI server for the Autonomous Code Agent.

Endpoints
─────────
POST /run                   → start a new agent session, returns session_id
GET  /status/{session_id}   → poll for current status / pending approval
POST /approve/{session_id}  → approve or reject a pending tool call
GET  /sessions              → list all active session IDs
DELETE /sessions/{id}       → remove a session

Flow
────
1. Client POSTs to /run  →  agent starts in a background thread
2. When a tool needing approval is reached, the thread pauses (threading.Event)
   and session status becomes "waiting_approval"
3. Client GETs /status to see what needs approving
4. Client POSTs to /approve with {approved: true/false}
5. Background thread resumes, continues until next pause or finish
"""

import uuid
import threading
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from api.models import RunRequest, ApproveRequest, StatusResponse
from api.session_manager import session_manager, Session
from agent.state import AgentState
from agent.nodes import agent_node, tools_node
from config.settings import settings

app = FastAPI(
    title="Autonomous Code Agent API",
    description="Drive the code agent via REST — useful for UIs or integrations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Background worker
# ─────────────────────────────────────────────

def _agent_worker(session: Session):
    """Runs in a background thread. Drives the agent state machine."""
    state: AgentState = session.state
    max_iter = 50
    iteration = 0

    try:
        while state["next_action"] != "finish" and iteration < max_iter:
            iteration += 1
            action = state["next_action"]

            if action == "agent":
                session.status = "running"
                state = agent_node(state)
                session.state = state

                last = state["messages"][-1]
                if isinstance(last, AIMessage) and last.content:
                    session.last_message = last.content

            elif action == "tools":
                session.status = "running"
                state = tools_node(state)
                session.state = state

                last = state["messages"][-1]
                if isinstance(last, ToolMessage):
                    session.last_message = f"[Tool result] {last.content[:300]}"

            elif action in ("human_approval", "waiting_for_human"):
                # Pause and wait for /approve endpoint
                session.status = "waiting_approval"
                session.pending_tool = state.get("current_tool")
                session.pending_args = state.get("tool_args") or {}
                session.approval_event.clear()
                session.approval_event.wait()   # blocks until /approve is called

                if session.approved:
                    state = tools_node(state)
                    session.state = state
                    last = state["messages"][-1]
                    if isinstance(last, ToolMessage):
                        session.last_message = f"[Tool result] {last.content[:300]}"
                else:
                    # Rejected: inject ToolMessage and continue
                    rejection = ToolMessage(
                        content=(
                            f"The user rejected the call to '{state.get('current_tool')}'.\n"
                            "Please suggest an alternative or ask the user what to do."
                        ),
                        tool_call_id=state.get("tool_call_id", "rejected"),
                    )
                    state["messages"].append(rejection)
                    state["current_tool"] = None
                    state["tool_args"] = None
                    state["tool_call_id"] = None
                    state["human_decision"] = None
                    state["next_action"] = "agent"
                    session.state = state

                session.pending_tool = None
                session.pending_args = None
                session.approved = None

            else:
                # Unexpected — break out
                break

        session.status = "finished"

    except Exception as exc:
        session.status = "error"
        session.error = str(exc)


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.post("/run", response_model=StatusResponse, summary="Start a new agent session")
def run_agent(req: RunRequest):
    """
    Start the agent with a query. Optionally override the repo path.
    Returns a session_id you use for all subsequent calls.
    """
    session_id = str(uuid.uuid4())

    # Optionally override repo path for this session
    if req.repo_path:
        from pathlib import Path
        settings.repo_path = Path(req.repo_path)

    initial_state: AgentState = {
        "messages": [HumanMessage(content=req.query)],
        "next_action": "agent",
        "current_tool": None,
        "tool_args": None,
        "tool_call_id": None,
        "human_decision": None,
        "intermediate_steps": [],
        "error": None,
    }

    session = session_manager.create(session_id, initial_state)

    thread = threading.Thread(target=_agent_worker, args=(session,), daemon=True)
    thread.start()

    return StatusResponse(
        session_id=session_id,
        status="running",
        last_message="Agent started. Poll /status/{session_id} for updates.",
    )


@app.get("/status/{session_id}", response_model=StatusResponse, summary="Poll session status")
def get_status(session_id: str):
    """
    Returns the current status of the agent session.

    - **running** — agent is thinking / calling tools
    - **waiting_approval** — agent wants to call a tool that needs your approval.
      Check `pending_tool` and `pending_args`, then POST to `/approve/{session_id}`.
    - **finished** — task complete
    - **error** — something went wrong; see `error` field
    """
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return StatusResponse(
        session_id=session_id,
        status=session.status,
        pending_tool=session.pending_tool,
        pending_args=session.pending_args,
        last_message=session.last_message,
        error=session.error,
    )


@app.post("/approve/{session_id}", response_model=StatusResponse, summary="Approve or reject a pending tool call")
def approve(session_id: str, req: ApproveRequest):
    """
    Respond to a pending approval request.

    - `approved: true` → tool will be executed
    - `approved: false` → tool is rejected; agent will re-plan
    """
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    if session.status != "waiting_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Session is not waiting for approval (current status: {session.status}).",
        )

    session.approved = req.approved
    session.status = "running"
    session.approval_event.set()   # unblock the worker thread

    return StatusResponse(
        session_id=session_id,
        status="running",
        last_message=f"{'Approved' if req.approved else 'Rejected'} — agent resuming.",
    )


@app.get("/sessions", response_model=List[str], summary="List all active session IDs")
def list_sessions():
    return session_manager.list_ids()


@app.delete("/sessions/{session_id}", summary="Delete a session")
def delete_session(session_id: str):
    if not session_manager.get(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    session_manager.delete(session_id)
    return {"deleted": session_id}


@app.get("/", summary="Health check")
def root():
    return {
        "service": "Autonomous Code Agent API",
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "repo_path": str(settings.repo_path),
    }
