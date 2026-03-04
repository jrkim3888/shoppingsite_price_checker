from __future__ import annotations

from typing import Any
from urllib.request import Request, urlopen
from urllib.parse import quote
import json
import re

from app.adapters.base import SiteAdapter
from app.schemas import ProductItem


class ElevenStAdapter(SiteAdapter):
    site = "11st"

    def _fetch_json(self, query: str, page_no: int) -> dict[str, Any]:
        q = quote(query)
        url = f"https://apis.11st.co.kr/search/api/tab?kwd={q}&tabId=TOTAL_SEARCH&poc=pc&pageNo={page_no}"
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
                "Referer": f"https://search.11st.co.kr/pc/total-search?kwd={q}&tabId=TOTAL_SEARCH",
                "Origin": "https://search.11st.co.kr",
            },
        )
        with urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))

    def _to_item(self, row: dict[str, Any], source_url: str) -> ProductItem | None:
        title = row.get("title")
        raw_link = row.get("linkUrl")
        product_id = row.get("id")
        product_url = f"https://www.11st.co.kr/products/{product_id}" if product_id else raw_link
        if not title or not product_url:
            return None

        image = row.get("imageUrl")
        brand = row.get("sellerNm") or row.get("brandNm") or None

        price = None
        if isinstance(row.get("finalPrc"), int):
            price = row.get("finalPrc")
        elif isinstance(row.get("selPrc"), int):
            price = row.get("selPrc")

        rating = None
        if isinstance(row.get("satisfactionScore"), (int, float)):
            rating = float(row.get("satisfactionScore"))

        review_count = None
        rtxt = row.get("reviewCountText")
        if isinstance(rtxt, str):
            m = re.search(r"(\d[\d,]*)", rtxt)
            if m:
                review_count = int(m.group(1).replace(",", ""))

        return ProductItem(
            title=title,
            brand=brand,
            price=price,
            product_url=product_url,
            source_url=source_url,
            images=[image] if image else [],
            thumbnail=image,
            rating=rating,
            review_count=review_count,
            review_summary=[],
            raw_reviews_sample=[],
            attributes={},
        )

    async def search(self, query: str, filters: dict[str, Any], page_cursor: str | None, limit: int) -> dict[str, Any]:
        page_no = int(page_cursor or "1")
        try:
            payload = self._fetch_json(query, page_no)
        except Exception:
            return {"items": [], "next_cursor": None}

        source_url = f"https://search.11st.co.kr/pc/total-search?kwd={quote(query)}&tabId=TOTAL_SEARCH"
        candidates: list[ProductItem] = []

        for group in payload.get("data", []):
            items = group.get("items") if isinstance(group, dict) else None
            if not isinstance(items, list):
                continue
            for row in items:
                if not isinstance(row, dict):
                    continue
                it = self._to_item(row, source_url)
                if it:
                    candidates.append(it)

        # price filter
        pr = filters.get("price_range") if isinstance(filters, dict) else None
        min_price = pr[0] if isinstance(pr, list) and len(pr) == 2 and isinstance(pr[0], int) else None
        max_price = pr[1] if isinstance(pr, list) and len(pr) == 2 and isinstance(pr[1], int) else None
        if min_price is not None or max_price is not None:
            out = []
            for it in candidates:
                if it.price is None:
                    out.append(it)
                    continue
                if min_price is not None and it.price < min_price:
                    continue
                if max_price is not None and it.price > max_price:
                    continue
                out.append(it)
            candidates = out

        # dedupe + clip
        seen = set()
        items: list[ProductItem] = []
        for it in candidates:
            if it.product_url in seen:
                continue
            seen.add(it.product_url)
            items.append(it)
            if len(items) >= max(1, min(limit, 80)):
                break

        cur_page = int(payload.get("curPage") or page_no)
        total_page = int(payload.get("totalPage") or cur_page)
        next_cursor = str(cur_page + 1) if cur_page < total_page else None

        return {"items": items, "next_cursor": next_cursor}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {"product_url": product_url}

    async def fetch_reviews(self, product_url: str, cursor: str | None = None, limit: int = 10) -> dict[str, Any]:
        return {"items": [], "next_cursor": None}
