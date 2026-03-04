from __future__ import annotations

from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json

from app.adapters.base import SiteAdapter
from app.schemas import ProductItem


class TwentyNineCmAdapter(SiteAdapter):
    site = "29cm"

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "https://www.29cm.co.kr",
                "Referer": "https://www.29cm.co.kr/store/search",
            },
            method="POST",
        )
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))

    async def search(self, query: str, filters: dict[str, Any], page_cursor: str | None, limit: int, sort: str = "popular") -> dict[str, Any]:
        size = max(1, min(limit, 100))

        sort_type_map = {
            "popular": "RECOMMENDED",
            "rating_desc": "MOST_REVIEWED",
            "review_count_desc": "MOST_REVIEWED",
        }
        sort_type = sort_type_map.get(sort, "RECOMMENDED")
        page = int(page_cursor) if page_cursor else 1
        body = {
            "keyword": query,
            "pageRequest": {"page": page, "size": size},
            "pageType": "SRP",
            "sortType": sort_type,
        }
        try:
            payload = self._post_json(
                "https://display-bff-api.29cm.co.kr/api/v1/listing/items?colorchipVariant=treatment",
                body,
            )
        except HTTPError:
            return {"items": [], "next_cursor": None}

        min_price: int | None = None
        max_price: int | None = None
        pr = filters.get("price_range") if isinstance(filters, dict) else None
        if isinstance(pr, list) and len(pr) == 2:
            if isinstance(pr[0], int):
                min_price = pr[0]
            if isinstance(pr[1], int):
                max_price = pr[1]

        items: list[ProductItem] = []
        for row in payload.get("data", {}).get("list", []):
            info = row.get("itemInfo", {})
            price = info.get("displayPrice") if isinstance(info.get("displayPrice"), int) else None
            if min_price is not None and isinstance(price, int) and price < min_price:
                continue
            if max_price is not None and isinstance(price, int) and price > max_price:
                continue

            product_url = row.get("itemUrl", {}).get("webLink") or f"https://product.29cm.co.kr/catalog/{row.get('itemId')}"
            thumb = info.get("thumbnailUrl")
            review_score = info.get("reviewScore")
            review_count = info.get("reviewCount")
            color_opts = [c.get("name") for c in (info.get("itemGroup", {}).get("colors", []) or []) if c.get("name")]

            items.append(
                ProductItem(
                    title=info.get("productName") or f"상품 {row.get('itemId')}",
                    brand=info.get("brandName"),
                    price=price,
                    product_url=product_url,
                    source_url=f"https://www.29cm.co.kr/store/search?keyword={query}",
                    images=[thumb] if thumb else [],
                    thumbnail=thumb,
                    rating=float(review_score) if isinstance(review_score, (int, float)) else None,
                    review_count=review_count if isinstance(review_count, int) else None,
                    review_summary=[],
                    raw_reviews_sample=[],
                    attributes={"color_options": color_opts},
                )
            )

        page_info = payload.get("data", {}).get("pagination", {})
        has_next = bool(page_info.get("hasNext"))

        next_cursor = str(page + 1) if has_next else None

        return {"items": items, "next_cursor": next_cursor}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {"product_url": product_url}

    async def fetch_reviews(self, product_url: str, cursor: str | None = None, limit: int = 10) -> dict[str, Any]:
        return {"items": [], "next_cursor": None}
