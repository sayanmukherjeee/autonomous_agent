"""
Entry point for the CLI.

Usage (from the project root with venv activated):
    python run_cli.py
"""

import logging
import sys
from pathlib import Path

# ── Ensure project root is on sys.path (needed if run from elsewhere) ──
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings

# ── Configure logging ──
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("agent.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Suppress noisy third-party loggers
for noisy in ("httpx", "httpcore", "urllib3", "langchain", "langgraph"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from cli.console import run_cli

if __name__ == "__main__":
    run_cli()
