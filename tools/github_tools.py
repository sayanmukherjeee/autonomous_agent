"""
GitHub integration tools (PyGithub + local git subprocess).
⚠️  create_branch, commit_and_push, create_pr require human approval.
"""

import subprocess
from langchain_core.tools import tool
from config.settings import settings


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _git(args: list, cwd=None) -> str:
    """Run a git command and return stdout, raising on error."""
    cwd = str(cwd or settings.repo_path)
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def _get_repo_full_name() -> str:
    """Parse 'user/repo' from the remote origin URL."""
    remote_url = _git(["config", "--get", "remote.origin.url"])
    # Handles both:
    #   git@github.com:user/repo.git
    #   https://github.com/user/repo.git
    if "github.com:" in remote_url:
        full = remote_url.split("github.com:")[1]
    elif "github.com/" in remote_url:
        full = remote_url.split("github.com/")[1]
    else:
        raise ValueError(f"Cannot parse GitHub repo from remote URL: {remote_url}")
    return full.replace(".git", "").strip()


def _get_github_repo():
    """Return a PyGithub Repository object."""
    if not settings.github_token or settings.github_token.startswith("your_"):
        raise ValueError(
            "GITHUB_TOKEN is not set in .env.\n"
            "Go to GitHub → Settings → Developer settings → PAT and create a token."
        )
    from github import Github
    g = Github(settings.github_token)
    return g.get_repo(_get_repo_full_name())


# ─────────────────────────────────────────────
# LangChain tools
# ─────────────────────────────────────────────

@tool
def create_branch(branch_name: str, base_branch: str = "main") -> str:
    """
    Create and switch to a new local git branch from base_branch.
    ⚠️  Requires human approval before execution.

    Args:
        branch_name: Name for the new branch, e.g. 'fix/division-by-zero'.
        base_branch: Branch to branch off from (default: 'main').
    """
    try:
        _git(["checkout", base_branch])
        _git(["pull"])
        _git(["checkout", "-b", branch_name])
        return f"✅ Branch '{branch_name}' created from '{base_branch}'."
    except RuntimeError as e:
        return f"❌ {e}"


@tool
def commit_and_push(message: str, branch: str = "") -> str:
    """
    Stage all changes, commit with a message, and push to origin.
    ⚠️  Requires human approval before execution.

    Args:
        message: Commit message.
        branch: Branch to push to. If empty, uses the current branch.
    """
    try:
        _git(["add", "."])
        # Check if there's anything to commit
        status = _git(["status", "--porcelain"])
        if not status:
            return "ℹ️  Nothing to commit — working tree is clean."
        _git(["commit", "-m", message])
        target_branch = branch.strip() or _git(["rev-parse", "--abbrev-ref", "HEAD"])
        _git(["push", "origin", target_branch])
        return f"✅ Committed and pushed to origin/{target_branch}."
    except RuntimeError as e:
        return f"❌ {e}"


@tool
def create_pr(title: str, body: str, head: str, base: str = "main") -> str:
    """
    Create a GitHub Pull Request from head branch into base branch.
    ⚠️  Requires human approval before execution.

    Args:
        title: PR title.
        body: PR description / body text.
        head: Source branch name (the branch with your changes).
        base: Target branch (default: 'main').
    """
    try:
        repo = _get_github_repo()
        pr = repo.create_pull(title=title, body=body, head=head, base=base)
        return f"✅ PR created: {pr.html_url}"
    except Exception as e:
        return f"❌ Failed to create PR: {e}"


@tool
def get_issue(issue_number: int) -> str:
    """
    Fetch the title and body of a GitHub issue.

    Args:
        issue_number: The integer issue number (e.g. 42).
    """
    try:
        repo = _get_github_repo()
        issue = repo.get_issue(issue_number)
        return (
            f"Issue #{issue.number}: {issue.title}\n"
            f"State: {issue.state}\n\n"
            f"{issue.body or '(no description)'}"
        )
    except Exception as e:
        return f"❌ Failed to fetch issue #{issue_number}: {e}"
