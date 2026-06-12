from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any

from ..env import get_paths


ENV_KEYS = {
    "brave": "BRAVE_SEARCH_API_KEY",
    "exa": "EXA_API_KEY",
    "tavily": "TAVILY_API_KEY",
}


@dataclass(frozen=True)
class ProviderConfig:
    search: str = "auto"
    extract: str = "auto"
    api_keys: dict[str, str] = field(default_factory=dict)
    config_path: str | None = None

    def api_key(self, provider: str) -> str | None:
        env_key = ENV_KEYS.get(provider)
        if env_key:
            value = os.environ.get(env_key, "").strip()
            if value:
                return value
        value = self.api_keys.get(provider, "")
        return value.strip() or None


def load_provider_config(
    *,
    search_override: str | None = None,
    extract_override: str | None = None,
) -> ProviderConfig:
    data = _load_local_config()
    providers = data.get("providers") if isinstance(data.get("providers"), dict) else {}
    api_keys = providers.get("api_keys") if isinstance(providers.get("api_keys"), dict) else {}
    return ProviderConfig(
        search=(search_override or providers.get("search") or "auto").strip(),
        extract=(extract_override or providers.get("extract") or "auto").strip(),
        api_keys={str(k): str(v) for k, v in api_keys.items()},
        config_path=str(_config_path()) if _config_path().exists() else None,
    )


def _config_path() -> Path:
    return get_paths().state_dir / "config.json"


def _load_local_config() -> dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
