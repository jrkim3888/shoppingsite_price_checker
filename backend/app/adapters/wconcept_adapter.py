from __future__ import annotations

from typing import Any
from app.adapters.base import SiteAdapter


class WConceptAdapter(SiteAdapter):
    site = "wconcept"

    async def search(self, query: str, filters: dict[str, Any], page_cursor: str | None, limit: int) -> dict[str, Any]:
        # NOTE: W컨셉 공개 검색 API는 인증 토큰/키 제약으로 서버 단독 호출 시 차단됨.
        # 현재는 안전하게 빈 결과를 반환하고, 브라우저 릴레이 경유 수집으로 확장 예정.
        return {"items": [], "next_cursor": None}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {"product_url": product_url}

    async def fetch_reviews(self, product_url: str, cursor: str | None = None, limit: int = 10) -> dict[str, Any]:
        return {"items": [], "next_cursor": None}
