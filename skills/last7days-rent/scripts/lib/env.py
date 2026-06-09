from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_STATE_DIR = Path.home() / ".nesthub-rent"


@dataclass(frozen=True)
class LocalPaths:
    state_dir: Path
    profile_json: Path
    profile_md: Path
    feedback_jsonl: Path
    reports_dir: Path


def get_state_dir() -> Path:
    override = os.environ.get("LAST7DAYS_RENT_HOME")
    return Path(override).expanduser() if override else DEFAULT_STATE_DIR


def get_paths() -> LocalPaths:
    state_dir = get_state_dir()
    return LocalPaths(
        state_dir=state_dir,
        profile_json=state_dir / "profile.json",
        profile_md=state_dir / "profile.md",
        feedback_jsonl=state_dir / "feedback.jsonl",
        reports_dir=state_dir / "reports",
    )


def ensure_local_dirs(paths: LocalPaths | None = None) -> LocalPaths:
    paths = paths or get_paths()
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    return paths
