from __future__ import annotations

from typing import Any

from app.adapters.base import SiteAdapter
from app.schemas import ProductItem


class MockAdapter(SiteAdapter):
    def __init__(self, site: str):
        self.site = site  # type: ignore[assignment]

    async def search(
        self,
        query: str,
        filters: dict[str, Any],
        page_cursor: str | None,
        limit: int,
    ) -> dict[str, Any]:
        items: list[ProductItem] = []
        for i in range(limit):
            idx = i + 1
            items.append(
                ProductItem(
                    title=f"[{self.site}] {query} 샘플 상품 {idx}",
                    brand="sample-brand",
                    price=39000 + (idx * 1000),
                    product_url=f"https://example.com/{self.site}/product/{idx}",
                    source_url=f"https://example.com/{self.site}/search?q={query}",
                    images=[f"https://picsum.photos/seed/{self.site}-{idx}/640/800"],
                    thumbnail=f"https://picsum.photos/seed/{self.site}-{idx}/320/400",
                    rating=4.2,
                    review_count=10 + idx,
                    review_summary=[
                        "정사이즈라는 후기가 많음",
                        "봄에 입기 적당한 두께감",
                        "색감이 차분하다는 의견이 많음",
                    ],
                    attributes={"color_options": ["beige", "ivory", "navy"]},
                )
            )
        return {"items": items, "next_cursor": "page-2"}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {
            "product_url": product_url,
            "images": ["https://picsum.photos/seed/detail/1000/1200"],
            "attributes": {"material": "cotton blend"},
        }

    async def fetch_reviews(
        self,
        product_url: str,
        cursor: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        return {
            "items": [{"text": "원단이 부드럽고 봄에 입기 좋아요", "meta": {"option": "베이지"}}],
            "next_cursor": None,
        }
