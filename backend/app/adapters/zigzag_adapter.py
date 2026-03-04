from __future__ import annotations

from typing import Any
from urllib.request import Request, urlopen
import json

from app.adapters.base import SiteAdapter
from app.schemas import ProductItem


class ZigzagAdapter(SiteAdapter):
    site = "zigzag"

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "https://www.zigzag.kr",
                "Referer": "https://www.zigzag.kr/search",
            },
            method="POST",
        )
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))

    async def search(self, query: str, filters: dict[str, Any], page_cursor: str | None, limit: int, sort: str = "popular") -> dict[str, Any]:
        size = max(1, min(limit, 100))
        variables = {
            "input": {
                "initial": page_cursor is None,
                "page_id": "srp_item",
                "q": query,
                "after": page_cursor,
                "filter_id_list": [],
                "filter_list": [],
                "sub_filter_id_list": [],
            }
        }
        gql = {
            "operationName": "GetSearchResult",
            "query": "query GetSearchResult($input: SearchResultInput!) { search_result(input:$input) { total_count has_next end_cursor ui_item_list { ... on UxGoodsCardItem { title price product_url image_url shop_name review_score display_review_count } } } }",
            "variables": variables,
        }
        payload = self._post_json("https://api.zigzag.kr/api/2/graphql/GetSearchResult", gql)

        min_price: int | None = None
        max_price: int | None = None
        pr = filters.get("price_range") if isinstance(filters, dict) else None
        if isinstance(pr, list) and len(pr) == 2:
            if isinstance(pr[0], int):
                min_price = pr[0]
            if isinstance(pr[1], int):
                max_price = pr[1]

        items: list[ProductItem] = []
        ui = payload.get("data", {}).get("search_result", {}).get("ui_item_list", [])
        for row in ui:
            title = row.get("title")
            product_url = row.get("product_url")
            image_url = row.get("image_url")
            price = row.get("price") if isinstance(row.get("price"), int) else None
            if not title or not product_url:
                continue
            if min_price is not None and isinstance(price, int) and price < min_price:
                continue
            if max_price is not None and isinstance(price, int) and price > max_price:
                continue

            review_count = None
            rv = row.get("display_review_count")
            if isinstance(rv, str):
                try:
                    review_count = int(rv.replace(",", ""))
                except ValueError:
                    review_count = None

            items.append(
                ProductItem(
                    title=title,
                    brand=row.get("shop_name"),
                    price=price,
                    product_url=product_url,
                    source_url=f"https://www.zigzag.kr/search?q={query}",
                    images=[image_url] if image_url else [],
                    thumbnail=image_url,
                    rating=float(row.get("review_score")) if isinstance(row.get("review_score"), (int, float)) else None,
                    review_count=review_count,
                    review_summary=[],
                    raw_reviews_sample=[],
                    attributes={},
                )
            )
            if len(items) >= size:
                break

        next_cursor = payload.get("data", {}).get("search_result", {}).get("end_cursor")
        return {"items": items, "next_cursor": next_cursor}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {"product_url": product_url}

    async def fetch_reviews(self, product_url: str, cursor: str | None = None, limit: int = 10) -> dict[str, Any]:
        return {"items": [], "next_cursor": None}
