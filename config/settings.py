"""
Central configuration.
Priority: environment variables (.env) > config.yaml > built-in defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import yaml
from pydantic import BaseModel, Field

# Load .env from project root (works even when called from subdirectory)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


def _load_yaml() -> dict:
    yaml_path = Path(__file__).parent.parent / "config.yaml"
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


class Settings(BaseModel):
    # LLM
    llm_provider: str = "ollama"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    temperature: float = 0.2

    # Paths
    repo_path: Path = Field(default_factory=Path.cwd)

    # GitHub
    github_token: str = ""

    # Safety
    require_approval_for: list = Field(
        default_factory=lambda: [
            "write_file",
            "run_command",
            "create_branch",
            "commit_and_push",
            "create_pr",
        ]
    )
    command_whitelist: list = Field(
        default_factory=lambda: ["git", "python", "pytest", "pip", "dir", "echo", "type"]
    )

    # Logging
    log_level: str = "INFO"

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def load(cls) -> "Settings":
        y = _load_yaml()
        llm_y = y.get("llm", {})
        safety_y = y.get("safety", {})
        paths_y = y.get("paths", {})
        log_y = y.get("logging", {})

        # repo_path: env wins, then yaml, then cwd
        repo_env = os.getenv("REPO_PATH")
        repo_yaml = paths_y.get("repo_path")
        if repo_env:
            repo_path = Path(repo_env)
        elif repo_yaml:
            repo_path = Path(repo_yaml)
        else:
            repo_path = Path.cwd()

        # command_whitelist
        whitelist_env = os.getenv("ALLOWED_COMMANDS")
        if whitelist_env:
            whitelist = [c.strip() for c in whitelist_env.split(",") if c.strip()]
        else:
            whitelist = safety_y.get(
                "command_whitelist", ["git", "python", "pytest", "pip", "dir", "echo", "type"]
            )

        return cls(
            llm_provider=os.getenv(
                "LLM_PROVIDER", llm_y.get("provider", "ollama")
            ),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=llm_y.get("gemini_model", "gemini-1.5-flash"),
            ollama_base_url=os.getenv(
                "OLLAMA_BASE_URL", llm_y.get("ollama_base_url", "http://localhost:11434")
            ),
            ollama_model=os.getenv(
                "OLLAMA_MODEL", llm_y.get("ollama_model", "gemma3:4b")
            ),
            temperature=float(llm_y.get("temperature", 0.2)),
            repo_path=repo_path,
            github_token=os.getenv("GITHUB_TOKEN", ""),
            require_approval_for=safety_y.get(
                "require_approval_for",
                ["write_file", "run_command", "create_branch", "commit_and_push", "create_pr"],
            ),
            command_whitelist=whitelist,
            log_level=os.getenv(
                "LOG_LEVEL", log_y.get("level", "INFO")
            ),
        )


# Singleton – import this everywhere
settings = Settings.load()
