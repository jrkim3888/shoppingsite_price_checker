from __future__ import annotations

from typing import Any
from app.adapters.base import SiteAdapter


class SsfAdapter(SiteAdapter):
    site = "ssf"

    async def search(self, query: str, filters: dict[str, Any], page_cursor: str | None, limit: int) -> dict[str, Any]:
        # SSF는 공개 검색 API 경로 식별 전 단계 (페이지 구조 복잡/동적)
        return {"items": [], "next_cursor": None}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {"product_url": product_url}

    async def fetch_reviews(self, product_url: str, cursor: str | None = None, limit: int = 10) -> dict[str, Any]:
        return {"items": [], "next_cursor": None}
