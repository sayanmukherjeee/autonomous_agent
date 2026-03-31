"""
Entry point for the FastAPI server.

Usage (from the project root with venv activated):
    python run_api.py

Then open:
    http://localhost:8000        → health check
    http://localhost:8000/docs  → Swagger UI (interactive API docs)
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("agent.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

for noisy in ("httpx", "httpcore", "urllib3", "langchain", "langgraph"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

import uvicorn
from api.main import app

if __name__ == "__main__":
    print(f"Starting API server…")
    print(f"  LLM provider : {settings.llm_provider}")
    print(f"  Repo path    : {settings.repo_path.resolve()}")
    print(f"  Swagger UI   : http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
