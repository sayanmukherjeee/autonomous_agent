"""
Terminal / shell command execution tool.
⚠️  Requires human approval before execution.
Commands are restricted to a configurable whitelist.
"""

import subprocess
import sys
from pathlib import Path
from langchain_core.tools import tool
from config.settings import settings


@tool
def run_command(command: str) -> str:
    """
    Execute a shell command inside the repository directory.
    ⚠️  Requires human approval before execution.
    Only commands whose first word is in the whitelist are allowed.

    Args:
        command: The full shell command string, e.g. 'python -m pytest tests/'.
    """
    # Whitelist check
    if settings.command_whitelist:
        first_word = command.strip().split()[0].lower()
        # strip path separators in case someone passes full path like C:/Python/python.exe
        first_word_base = Path(first_word).name
        allowed = any(
            first_word_base.startswith(prefix.lower())
            for prefix in settings.command_whitelist
        )
        if not allowed:
            return (
                f"❌ Command rejected by whitelist.\n"
                f"First word: '{first_word_base}'\n"
                f"Allowed prefixes: {settings.command_whitelist}\n"
                f"Add the prefix to ALLOWED_COMMANDS in .env if you need it."
            )

    cwd = str(settings.repo_path)

    # Choose shell based on OS
    if sys.platform == "win32":
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            executable="/bin/bash",
        )

    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += result.stderr

    if result.returncode != 0:
        return f"⚠️  Command exited with code {result.returncode}:\n{output}"
    return output or "(command produced no output)"
