from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_STATE_DIR = Path.home() / ".last7days-rent"


@dataclass(frozen=True)
class LocalPaths:
    state_dir: Path
    profile_json: Path
    profile_md: Path
    profiles_dir: Path
    pools_dir: Path
    feedback_jsonl: Path
    cache_dir: Path
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
        profiles_dir=state_dir / "profiles",
        pools_dir=state_dir / "pools",
        feedback_jsonl=state_dir / "feedback.jsonl",
        cache_dir=state_dir / "cache",
        reports_dir=state_dir / "reports",
    )


def ensure_local_dirs(paths: LocalPaths | None = None) -> LocalPaths:
    paths = paths or get_paths()
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.profiles_dir.mkdir(parents=True, exist_ok=True)
    paths.pools_dir.mkdir(parents=True, exist_ok=True)
    paths.cache_dir.mkdir(parents=True, exist_ok=True)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    return paths


def should_cache_raw() -> bool:
    return os.environ.get("LAST7DAYS_RENT_CACHE_RAW") == "1"


def http_timeout_seconds() -> float:
    raw = os.environ.get("LAST7DAYS_RENT_HTTP_TIMEOUT", "15")
    try:
        value = float(raw)
    except ValueError:
        return 15.0
    return max(1.0, min(value, 60.0))
