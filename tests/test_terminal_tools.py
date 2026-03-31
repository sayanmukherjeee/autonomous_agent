"""
Tests for terminal_tools.
Run:  python -m pytest tests/test_terminal_tools.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture(autouse=True)
def patch_repo_path(tmp_path):
    from config import settings as settings_module
    original = settings_module.settings.repo_path
    settings_module.settings.repo_path = tmp_path
    yield tmp_path
    settings_module.settings.repo_path = original


def test_echo_command():
    from tools.terminal_tools import run_command
    result = run_command.invoke({"command": "echo hello"})
    assert "hello" in result.lower()


def test_blocked_command():
    from tools.terminal_tools import run_command
    # "rm" is not in the default whitelist
    result = run_command.invoke({"command": "rm -rf /"})
    assert "rejected" in result.lower() or "whitelist" in result.lower()


def test_python_version():
    from tools.terminal_tools import run_command
    result = run_command.invoke({"command": "python --version"})
    assert "python" in result.lower() or "3." in result.lower()
