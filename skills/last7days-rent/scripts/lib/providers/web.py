from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..schema import ExtractedDocument, SearchHit
from ..sources.http import fetch_public_url
from .base import ExtractProvider, SearchProvider
from .config import ProviderConfig


class ProviderError(RuntimeError):
    pass


class BraveSearchProvider(SearchProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def name(self) -> str:
        return "brave"

    def is_available(self) -> bool:
        return bool(self.config.api_key("brave"))

    def search(self, query: str, limit: int = 5, **options: Any) -> list[SearchHit]:
        api_key = self.config.api_key("brave")
        if not api_key:
            raise ProviderError("BRAVE_SEARCH_API_KEY is not configured")
        count = max(1, min(int(limit), 20))
        url = "https://api.search.brave.com/res/v1/web/search?" + urlencode({"q": query, "count": count})
        data = _json_request(
            url,
            method="GET",
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        )
        results = ((data.get("web") or {}).get("results") or [])[:count]
        return [
            SearchHit(
                provider=self.name,
                query=query,
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                description=str(item.get("description") or ""),
                position=idx,
                raw=item if isinstance(item, dict) else {},
            )
            for idx, item in enumerate(results, start=1)
            if item.get("url")
        ]


class ExaProvider(SearchProvider, ExtractProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def name(self) -> str:
        return "exa"

    def is_available(self) -> bool:
        return bool(self.config.api_key("exa"))

    def search(self, query: str, limit: int = 5, **options: Any) -> list[SearchHit]:
        api_key = self.config.api_key("exa")
        if not api_key:
            raise ProviderError("EXA_API_KEY is not configured")
        data = _json_request(
            "https://api.exa.ai/search",
            method="POST",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            payload={"query": query, "numResults": max(1, int(limit)), "contents": {"highlights": True}},
        )
        results = data.get("results") or []
        hits: list[SearchHit] = []
        for idx, item in enumerate(results[:limit], start=1):
            highlights = item.get("highlights") if isinstance(item.get("highlights"), list) else []
            hits.append(
                SearchHit(
                    provider=self.name,
                    query=query,
                    title=str(item.get("title") or ""),
                    url=str(item.get("url") or ""),
                    description=" ".join(str(part) for part in highlights) or str(item.get("text") or ""),
                    position=idx,
                    raw=item if isinstance(item, dict) else {},
                )
            )
        return [hit for hit in hits if hit.url]

    def extract(self, urls: list[str], **options: Any) -> list[ExtractedDocument]:
        api_key = self.config.api_key("exa")
        if not api_key:
            raise ProviderError("EXA_API_KEY is not configured")
        if not urls:
            return []
        data = _json_request(
            "https://api.exa.ai/contents",
            method="POST",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            payload={"urls": urls, "text": True, "highlights": True, "maxAgeHours": 0},
        )
        by_url = {str(item.get("url") or ""): item for item in data.get("results") or [] if isinstance(item, dict)}
        docs: list[ExtractedDocument] = []
        for url in urls:
            item = by_url.get(url)
            if not item:
                docs.append(ExtractedDocument(provider=self.name, requested_url=url, status="failed", error="exa returned no result"))
                continue
            content = str(item.get("text") or "")
            docs.append(
                ExtractedDocument(
                    provider=self.name,
                    requested_url=url,
                    final_url=str(item.get("url") or url),
                    title=str(item.get("title") or ""),
                    content=content,
                    raw_content=content,
                    metadata=item,
                )
            )
        return docs


class TavilyProvider(SearchProvider, ExtractProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def name(self) -> str:
        return "tavily"

    def is_available(self) -> bool:
        return bool(self.config.api_key("tavily"))

    def search(self, query: str, limit: int = 5, **options: Any) -> list[SearchHit]:
        api_key = self.config.api_key("tavily")
        if not api_key:
            raise ProviderError("TAVILY_API_KEY is not configured")
        data = _json_request(
            "https://api.tavily.com/search",
            method="POST",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            payload={"query": query, "max_results": max(1, min(int(limit), 20)), "include_raw_content": False},
        )
        results = data.get("results") or []
        return [
            SearchHit(
                provider=self.name,
                query=query,
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                description=str(item.get("content") or item.get("description") or ""),
                position=idx,
                raw=item if isinstance(item, dict) else {},
            )
            for idx, item in enumerate(results[:limit], start=1)
            if item.get("url")
        ]

    def extract(self, urls: list[str], **options: Any) -> list[ExtractedDocument]:
        api_key = self.config.api_key("tavily")
        if not api_key:
            raise ProviderError("TAVILY_API_KEY is not configured")
        if not urls:
            return []
        data = _json_request(
            "https://api.tavily.com/extract",
            method="POST",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            payload={"urls": urls, "format": "markdown"},
        )
        docs: list[ExtractedDocument] = []
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            content = str(item.get("raw_content") or item.get("content") or "")
            docs.append(
                ExtractedDocument(
                    provider=self.name,
                    requested_url=str(item.get("url") or ""),
                    final_url=str(item.get("url") or ""),
                    title=str(item.get("title") or ""),
                    content=content,
                    raw_content=content,
                    metadata=item,
                )
            )
        for item in data.get("failed_results") or []:
            if isinstance(item, dict):
                docs.append(
                    ExtractedDocument(
                        provider=self.name,
                        requested_url=str(item.get("url") or ""),
                        status="failed",
                        error=str(item.get("error") or "tavily extract failed"),
                        metadata=item,
                    )
                )
        returned = {doc.requested_url for doc in docs}
        for url in urls:
            if url not in returned:
                docs.append(ExtractedDocument(provider=self.name, requested_url=url, status="failed", error="tavily returned no result"))
        return docs


class DDGSSearchProvider(SearchProvider):
    @property
    def name(self) -> str:
        return "ddgs"

    def is_available(self) -> bool:
        try:
            import ddgs  # noqa: F401

            return True
        except ImportError:
            return False

    def search(self, query: str, limit: int = 5, **options: Any) -> list[SearchHit]:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError as exc:
            raise ProviderError("ddgs package is not installed") from exc
        safe_limit = max(1, int(limit))
        hits: list[SearchHit] = []
        with DDGS() as client:
            for idx, item in enumerate(client.text(query, max_results=safe_limit), start=1):
                if idx > safe_limit:
                    break
                url = str(item.get("href") or item.get("url") or "")
                if not url:
                    continue
                hits.append(
                    SearchHit(
                        provider=self.name,
                        query=query,
                        title=str(item.get("title") or ""),
                        url=url,
                        description=str(item.get("body") or ""),
                        position=idx,
                        raw=item if isinstance(item, dict) else {},
                    )
                )
        return hits


class BasicHttpExtractProvider(ExtractProvider):
    @property
    def name(self) -> str:
        return "basic_http"

    def is_available(self) -> bool:
        return True

    def extract(self, urls: list[str], **options: Any) -> list[ExtractedDocument]:
        docs: list[ExtractedDocument] = []
        for url in urls:
            text, fetch = fetch_public_url("basic_http", url)
            docs.append(
                ExtractedDocument(
                    provider=self.name,
                    requested_url=url,
                    final_url=fetch.url,
                    title="",
                    content=text,
                    raw_content=text,
                    metadata=fetch.to_dict(),
                    status="ok" if fetch.status == "ok" else ("blocked" if fetch.status == "blocked" else "failed"),
                    error=fetch.warning,
                )
            )
        return docs


def _json_request(
    url: str,
    *,
    method: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=20) as response:
        text = response.read(2_000_000).decode("utf-8", errors="replace")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ProviderError("provider returned non-object JSON")
    return data
