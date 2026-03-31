"""
Pydantic request / response models for the FastAPI server.
"""

from typing import Optional
from pydantic import BaseModel


class RunRequest(BaseModel):
    query: str
    repo_path: Optional[str] = None


class ApproveRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


class StatusResponse(BaseModel):
    session_id: str
    status: str          # "running" | "waiting_approval" | "finished" | "error"
    pending_tool: Optional[str] = None
    pending_args: Optional[dict] = None
    last_message: Optional[str] = None
    error: Optional[str] = None
