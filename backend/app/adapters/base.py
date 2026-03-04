from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.schemas import ProductItem, SiteName


class SearchResultPage(dict):
    items: list[ProductItem]
    next_cursor: str | None


class SiteAdapter(ABC):
    site: SiteName

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: dict[str, Any],
        page_cursor: str | None,
        limit: int,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_reviews(
        self,
        product_url: str,
        cursor: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        raise NotImplementedError
