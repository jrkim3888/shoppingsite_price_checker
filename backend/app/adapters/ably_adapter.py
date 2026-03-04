from __future__ import annotations

from typing import Any
from app.adapters.base import SiteAdapter


class AblyAdapter(SiteAdapter):
    site = "ably"

    async def search(self, query: str, filters: dict[str, Any], page_cursor: str | None, limit: int) -> dict[str, Any]:
        # 서버 단독 요청이 Cloudflare 403으로 차단되어 현재 비활성화
        return {"items": [], "next_cursor": None}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {"product_url": product_url}

    async def fetch_reviews(self, product_url: str, cursor: str | None = None, limit: int = 10) -> dict[str, Any]:
        return {"items": [], "next_cursor": None}
