"""
In-memory session store.
Each session holds the current AgentState and a flag for pending approvals.

In production you'd persist this to Redis / a DB, but for a local tool
an in-process dict is fine.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import threading


@dataclass
class Session:
    session_id: str
    state: Dict[str, Any]
    status: str = "running"          # running | waiting_approval | finished | error
    pending_tool: Optional[str] = None
    pending_args: Optional[dict] = None
    last_message: Optional[str] = None
    error: Optional[str] = None
    # threading event used to resume execution after approval
    approval_event: threading.Event = field(default_factory=threading.Event)
    approved: Optional[bool] = None  # set by /approve endpoint


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, session_id: str, initial_state: dict) -> Session:
        session = Session(session_id=session_id, state=initial_state)
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def list_ids(self):
        return list(self._sessions.keys())


# Singleton
session_manager = SessionManager()
