from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..schema import ExtractedDocument, SearchHit


class SearchProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, limit: int = 5, **options: Any) -> list[SearchHit]:
        raise NotImplementedError


class ExtractProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract(self, urls: list[str], **options: Any) -> list[ExtractedDocument]:
        raise NotImplementedError
