"""
Tests for file_tools.
Run:  python -m pytest tests/test_file_tools.py -v
"""

import sys
from pathlib import Path

# Make sure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import tempfile
import os


@pytest.fixture(autouse=True)
def patch_repo_path(tmp_path):
    """Redirect settings.repo_path to a temp directory for every test."""
    from config import settings as settings_module
    original = settings_module.settings.repo_path
    settings_module.settings.repo_path = tmp_path
    yield tmp_path
    settings_module.settings.repo_path = original


def test_write_and_read_file(tmp_path):
    from tools.file_tools import write_file, read_file
    write_file.invoke({"path": "hello.txt", "content": "Hello, world!"})
    result = read_file.invoke({"path": "hello.txt"})
    assert result == "Hello, world!"


def test_read_missing_file():
    from tools.file_tools import read_file
    result = read_file.invoke({"path": "does_not_exist.txt"})
    assert "ERROR" in result


def test_list_directory(tmp_path):
    from tools.file_tools import write_file, list_directory
    write_file.invoke({"path": "a.py", "content": "# a"})
    write_file.invoke({"path": "b.py", "content": "# b"})
    result = list_directory.invoke({"path": "."})
    assert "a.py" in result
    assert "b.py" in result


def test_search_files(tmp_path):
    from tools.file_tools import write_file, search_files
    write_file.invoke({"path": "src/main.py", "content": "print('hi')"})
    write_file.invoke({"path": "src/utils.py", "content": "pass"})
    result = search_files.invoke({"pattern": "**/*.py", "directory": "."})
    assert "main.py" in result
    assert "utils.py" in result


def test_path_traversal_blocked():
    from tools.file_tools import read_file
    result = read_file.invoke({"path": "../../etc/passwd"})
    assert "ERROR" in result or "Security" in result
