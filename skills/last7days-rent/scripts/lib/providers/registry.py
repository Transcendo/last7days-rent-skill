from __future__ import annotations

from dataclasses import dataclass

from ..schema import ProviderDiagnostic
from .base import ExtractProvider, SearchProvider
from .config import ProviderConfig
from .web import BasicHttpExtractProvider, BraveSearchProvider, DDGSSearchProvider, ExaProvider, TavilyProvider


SEARCH_ORDER = ("brave", "exa", "tavily", "ddgs")
EXTRACT_ORDER = ("exa", "tavily", "basic_http")


@dataclass
class ProviderResolution:
    search_provider: SearchProvider
    extract_provider: ExtractProvider
    diagnostics: list[ProviderDiagnostic]


class ProviderRegistry:
    def __init__(self, config: ProviderConfig):
        self.config = config
        exa = ExaProvider(config)
        tavily = TavilyProvider(config)
        self.search_providers: dict[str, SearchProvider] = {
            "brave": BraveSearchProvider(config),
            "exa": exa,
            "tavily": tavily,
            "ddgs": DDGSSearchProvider(),
        }
        self.extract_providers: dict[str, ExtractProvider] = {
            "exa": exa,
            "tavily": tavily,
            "basic_http": BasicHttpExtractProvider(),
        }

    def resolve(self) -> ProviderResolution:
        diagnostics: list[ProviderDiagnostic] = []
        search_provider = self._resolve_search(diagnostics)
        extract_provider = self._resolve_extract(diagnostics)
        return ProviderResolution(search_provider, extract_provider, diagnostics)

    def _resolve_search(self, diagnostics: list[ProviderDiagnostic]) -> SearchProvider:
        return self._resolve(
            requested=self.config.search,
            capability="search",
            providers=self.search_providers,
            order=SEARCH_ORDER,
            diagnostics=diagnostics,
        )

    def _resolve_extract(self, diagnostics: list[ProviderDiagnostic]) -> ExtractProvider:
        return self._resolve(
            requested=self.config.extract,
            capability="extract",
            providers=self.extract_providers,
            order=EXTRACT_ORDER,
            diagnostics=diagnostics,
        )

    def _resolve(
        self,
        *,
        requested: str,
        capability: str,
        providers: dict,
        order: tuple[str, ...],
        diagnostics: list[ProviderDiagnostic],
    ):
        requested = (requested or "auto").strip()
        if requested != "auto":
            provider = providers.get(requested)
            if provider and provider.is_available():
                diagnostics.append(_diag(capability, requested, requested, requested, "selected", None))
                return provider
            message = f"{requested} unavailable; falling back to auto"
            diagnostics.append(_diag(capability, requested, None, requested, "warning", message))

        for name in order:
            provider = providers[name]
            if provider.is_available():
                diagnostics.append(_diag(capability, requested, name, name, "selected", None))
                return provider
            diagnostics.append(_diag(capability, requested, None, name, "unavailable", _unavailable_reason(name)))
        # basic_http is always available for extract; ddgs should be installed as dependency for search.
        fallback = providers[order[-1]]
        diagnostics.append(_diag(capability, requested, fallback.name, fallback.name, "fallback", "using last configured fallback"))
        return fallback


def _diag(capability: str, requested: str, active: str | None, provider: str, status: str, message: str | None) -> ProviderDiagnostic:
    return ProviderDiagnostic(
        capability=capability,  # type: ignore[arg-type]
        requested_provider=requested,
        active_provider=active,
        provider=provider,
        status=status,  # type: ignore[arg-type]
        message=message,
    )


def _unavailable_reason(provider: str) -> str:
    if provider == "brave":
        return "missing BRAVE_SEARCH_API_KEY"
    if provider == "exa":
        return "missing EXA_API_KEY"
    if provider == "tavily":
        return "missing TAVILY_API_KEY"
    if provider == "ddgs":
        return "ddgs package is not importable"
    return "not available"
