"""
Tests for github_tools.
GitHub operations require a real token + repo — these tests mock the git subprocess.
Run:  python -m pytest tests/test_github_tools.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch, MagicMock


def test_get_issue_no_token():
    """get_issue should return an error string when token is missing."""
    from config import settings as settings_module
    original = settings_module.settings.github_token
    settings_module.settings.github_token = "your_personal_access_token_here"

    from tools.github_tools import get_issue
    result = get_issue.invoke({"issue_number": 1})
    assert "Failed" in result or "GITHUB_TOKEN" in result

    settings_module.settings.github_token = original


def test_create_branch_git_failure(tmp_path):
    """create_branch should return an error string if git fails."""
    from config import settings as settings_module
    original = settings_module.settings.repo_path
    settings_module.settings.repo_path = tmp_path  # not a git repo

    from tools.github_tools import create_branch
    result = create_branch.invoke({"branch_name": "test-branch", "base_branch": "main"})
    assert "❌" in result or "error" in result.lower() or "failed" in result.lower()

    settings_module.settings.repo_path = original
