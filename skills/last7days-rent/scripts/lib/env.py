from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_STATE_DIR = Path.home() / ".last7days-rent"
SEARCH_PROVIDER_ORDER = ["brave", "tavily", "exa"]


@dataclass(frozen=True)
class LocalPaths:
    state_dir: Path
    profile_json: Path
    profile_md: Path
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
        feedback_jsonl=state_dir / "feedback.jsonl",
        cache_dir=state_dir / "cache",
        reports_dir=state_dir / "reports",
    )


def ensure_local_dirs(paths: LocalPaths | None = None) -> LocalPaths:
    paths = paths or get_paths()
    paths.state_dir.mkdir(parents=True, exist_ok=True)
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


def provider_api_key(provider: str) -> str | None:
    if provider == "brave":
        return os.environ.get("BRAVE_SEARCH_API_KEY") or os.environ.get("BRAVE_API_KEY")
    if provider == "tavily":
        return os.environ.get("TAVILY_API_KEY")
    if provider == "exa":
        return os.environ.get("EXA_API_KEY")
    return None


def normalize_search_providers(providers: list[str] | None = None) -> list[str]:
    raw = providers or ["auto"]
    if len(raw) == 1 and raw[0] == "auto":
        return list(SEARCH_PROVIDER_ORDER)
    normalized: list[str] = []
    for provider in raw:
        value = provider.strip().lower()
        if not value or value == "auto":
            for item in SEARCH_PROVIDER_ORDER:
                if item not in normalized:
                    normalized.append(item)
            continue
        if value not in SEARCH_PROVIDER_ORDER:
            raise ValueError(f"unknown search provider: {provider}")
        if value not in normalized:
            normalized.append(value)
    return normalized or list(SEARCH_PROVIDER_ORDER)
