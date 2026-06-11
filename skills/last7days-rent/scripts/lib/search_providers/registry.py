from __future__ import annotations

from ..env import SEARCH_PROVIDER_ORDER, provider_api_key


def search_provider_registry() -> dict[str, dict]:
    return {
        "runtime_web_search": {
            "provider": "runtime_web_search",
            "env_keys": [],
            "endpoint": "host Agent web_search JSON import",
            "role": "Primary SearchLead discovery import from Codex/Claude/Hermes-style runtime web search",
            "enabled": True,
            "has_api_key": True,
        },
        "brave": {
            "provider": "brave",
            "env_keys": ["BRAVE_SEARCH_API_KEY", "BRAVE_API_KEY"],
            "endpoint": "https://api.search.brave.com/res/v1/web/search",
            "role": "SearchLead discovery only",
            "enabled": True,
            "has_api_key": bool(provider_api_key("brave")),
        },
        "tavily": {
            "provider": "tavily",
            "env_keys": ["TAVILY_API_KEY"],
            "endpoint": "https://api.tavily.com/search",
            "role": "SearchLead discovery only; extract is opt-in manual verification",
            "enabled": True,
            "has_api_key": bool(provider_api_key("tavily")),
        },
        "exa": {
            "provider": "exa",
            "env_keys": ["EXA_API_KEY"],
            "endpoint": "https://api.exa.ai/search",
            "role": "SearchLead discovery only; summary is not fact extraction",
            "enabled": True,
            "has_api_key": bool(provider_api_key("exa")),
        },
    } | {provider: {} for provider in SEARCH_PROVIDER_ORDER if provider not in {"brave", "tavily", "exa"}}
