"""Configuration management for GitHub Projects integration."""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class GitHubProjectsConfig:
    """Configuration for GitHub Projects integration."""
    
    enabled: bool = False
    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None
    project_number: Optional[int] = None
    project_id: Optional[str] = None
    project_url: Optional[str] = None
    
    # Custom field IDs (populated after project creation)
    field_ids: Optional[dict[str, str]] = None
    
    # Last sync information
    last_synced_at: Optional[str] = None
    last_synced_tasks_md_hash: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "GitHubProjectsConfig":
        """Create from dictionary."""
        return cls(**data)


def get_config_path(repo_root: Path) -> Path:
    """Get the path to the config file."""
    config_dir = repo_root / ".specify"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "github-projects.json"


def load_config(repo_root: Path) -> GitHubProjectsConfig:
    """
    Load GitHub Projects configuration from .specify/github-projects.json.
    Returns a default config if file doesn't exist.
    """
    config_path = get_config_path(repo_root)
    
    if not config_path.exists():
        return GitHubProjectsConfig()
    
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
        return GitHubProjectsConfig.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError):
        # Return default config if file is corrupted
        return GitHubProjectsConfig()


def save_config(repo_root: Path, config: GitHubProjectsConfig) -> None:
    """
    Save GitHub Projects configuration to .specify/github-projects.json.
    """
    config_path = get_config_path(repo_root)
    config_path.parent.mkdir(exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)
