from __future__ import annotations

from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import quote
import json

from app.adapters.base import SiteAdapter
from app.schemas import ProductItem


class BrandiAdapter(SiteAdapter):
    site = "brandi"

    def _get_json(self, url: str, referer: str) -> dict[str, Any]:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
                "Referer": referer,
            },
        )
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))

    async def search(self, query: str, filters: dict[str, Any], page_cursor: str | None, limit: int) -> dict[str, Any]:
        offset = int(page_cursor or "0")
        size = max(1, min(limit, 50))
        q = quote(query)
        url = f"https://capi.brandi.co.kr/v1/web/search/products/{q}?offset={offset}&limit={size}&order=popular&total-count=true&is-first={'true' if offset == 0 else 'false'}&version=2210"
        try:
            payload = self._get_json(url, referer=f"https://www.brandi.co.kr/search?q={q}")
        except HTTPError:
            return {"items": [], "next_cursor": None}

        pr = filters.get("price_range") if isinstance(filters, dict) else None
        min_price = pr[0] if isinstance(pr, list) and len(pr) == 2 and isinstance(pr[0], int) else None
        max_price = pr[1] if isinstance(pr, list) and len(pr) == 2 and isinstance(pr[1], int) else None

        raw_items = payload.get("data", {}).get("items", [])
        items: list[ProductItem] = []
        for row in raw_items:
            price = row.get("price") if isinstance(row.get("price"), int) else None
            if min_price is not None and isinstance(price, int) and price < min_price:
                continue
            if max_price is not None and isinstance(price, int) and price > max_price:
                continue

            product_id = row.get("id") or row.get("product-id")
            product_url = f"https://www.brandi.co.kr/products/{product_id}" if product_id else "https://www.brandi.co.kr/"
            image = row.get("image-url") or row.get("image_url")
            review_count = row.get("review-count") if isinstance(row.get("review-count"), int) else None
            review_score = row.get("review-score") if isinstance(row.get("review-score"), (int, float)) else None

            items.append(
                ProductItem(
                    title=row.get("name") or row.get("title") or "상품",
                    brand=row.get("seller-name") or row.get("shop-name"),
                    price=price,
                    product_url=product_url,
                    source_url=f"https://www.brandi.co.kr/search?q={q}",
                    images=[image] if image else [],
                    thumbnail=image,
                    rating=float(review_score) if review_score is not None else None,
                    review_count=review_count,
                    review_summary=[],
                    raw_reviews_sample=[],
                    attributes={},
                )
            )

        next_cursor = str(offset + size) if len(raw_items) >= size else None
        return {"items": items, "next_cursor": next_cursor}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {"product_url": product_url}

    async def fetch_reviews(self, product_url: str, cursor: str | None = None, limit: int = 10) -> dict[str, Any]:
        return {"items": [], "next_cursor": None}
