"""
File system tools.
All paths are resolved relative to settings.repo_path and sandboxed to it.
"""

import glob
from pathlib import Path
from langchain_core.tools import tool
from config.settings import settings


def _resolve(path: str) -> Path:
    """Resolve *path* relative to repo_path and verify it stays inside."""
    base = settings.repo_path.resolve()
    full = (base / path).resolve()
    if not str(full).startswith(str(base)):
        raise PermissionError(
            f"Security violation: '{path}' resolves outside the repo ({base})."
        )
    return full


@tool
def read_file(path: str) -> str:
    """
    Read and return the full text content of a file inside the repository.

    Args:
        path: Path to the file, relative to the repo root.
    """
    full = _resolve(path)
    if not full.exists():
        return f"ERROR: File '{path}' does not exist."
    if full.is_dir():
        return f"ERROR: '{path}' is a directory, not a file."
    try:
        return full.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"ERROR: '{path}' is a binary file and cannot be read as text."


@tool
def write_file(path: str, content: str) -> str:
    """
    Write (overwrite or create) a file with the given text content.
    ⚠️  Requires human approval before execution.

    Args:
        path: Path relative to repo root.
        content: Full text content to write.
    """
    full = _resolve(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return f"✅ Successfully wrote {len(content)} chars to '{path}'."


@tool
def list_directory(path: str = ".") -> str:
    """
    List all files and sub-directories inside a directory.

    Args:
        path: Directory path relative to repo root (default: repo root).
    """
    dir_path = _resolve(path)
    if not dir_path.exists():
        return f"ERROR: Directory '{path}' does not exist."
    if not dir_path.is_dir():
        return f"ERROR: '{path}' is not a directory."
    entries = sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name))
    lines = []
    for entry in entries:
        rel = entry.relative_to(settings.repo_path)
        tag = "[DIR] " if entry.is_dir() else "[FILE]"
        lines.append(f"{tag} {rel}")
    return "\n".join(lines) if lines else "(empty directory)"


@tool
def search_files(pattern: str, directory: str = ".") -> str:
    """
    Search for files matching a glob pattern inside the repository.

    Args:
        pattern: Glob pattern, e.g. '**/*.py' or '*.txt'.
        directory: Sub-directory to search in (default: repo root).
    """
    search_dir = _resolve(directory)
    matches = glob.glob(str(search_dir / pattern), recursive=True)
    rel_matches = []
    for m in matches:
        try:
            rel_matches.append(str(Path(m).relative_to(settings.repo_path)))
        except ValueError:
            rel_matches.append(m)
    if not rel_matches:
        return f"No files found matching '{pattern}' in '{directory}'."
    return "\n".join(sorted(rel_matches))
