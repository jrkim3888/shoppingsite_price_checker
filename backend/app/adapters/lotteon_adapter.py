from __future__ import annotations

from typing import Any
from urllib.request import Request, urlopen
from urllib.parse import quote, unquote
import re

from app.adapters.base import SiteAdapter
from app.schemas import ProductItem


class LotteOnAdapter(SiteAdapter):
    site = "lotteon"

    def _fetch_html(self, query: str) -> str:
        q = quote(query)
        url = f"https://www.lotteon.com/search/search/search.ecn?render=search&platform=pc&q={q}"
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html,application/xhtml+xml",
                "Referer": "https://www.lotteon.com/",
            },
        )
        with urlopen(req, timeout=25) as resp:
            return resp.read().decode("utf-8", "ignore")

    def _extract(self, html: str) -> list[ProductItem]:
        # JS object fragments embedded in HTML
        pattern = re.compile(
            r'"productName"\s*:\s*"(?P<title>.*?)"\s*,.*?'
            r'"productImage"\s*:\s*"(?P<img>.*?)"\s*,.*?'
            r'"productLink"\s*:\s*"(?P<link>.*?)"\s*,.*?'
            r'"brandName"\s*:\s*"(?P<brand>.*?)"\s*,.*?'
            r'"priceInfo"\s*:\s*\[(?P<priceinfo>.*?)\]\s*,.*?'
            r'"reviewInfo"\s*:\s*\[(?P<reviewinfo>.*?)\]\s*,',
            re.S,
        )

        items: list[ProductItem] = []
        seen: set[str] = set()

        for m in pattern.finditer(html):
            title = unquote(m.group("title")).strip()
            image = m.group("img").strip()
            link = m.group("link").strip().replace("\\/", "/")
            brand = unquote(m.group("brand")).strip() or None

            if not link or link in seen:
                continue
            seen.add(link)

            final_price = None
            pm = re.search(r'"type"\s*:\s*"final"\s*,\s*"num"\s*:\s*(\d+)', m.group("priceinfo"), re.S)
            if pm:
                final_price = int(pm.group(1))

            rating = None
            rm = re.search(r'"type"\s*:\s*"score"\s*,\s*"num"\s*:\s*([0-9.]+)', m.group("reviewinfo"), re.S)
            if rm:
                rating = float(rm.group(1))

            review_count = None
            cm = re.search(r'"type"\s*:\s*"count"\s*,\s*"num"\s*:\s*(\d+)', m.group("reviewinfo"), re.S)
            if cm:
                review_count = int(cm.group(1))

            if not title:
                continue

            items.append(
                ProductItem(
                    title=title,
                    brand=brand,
                    price=final_price,
                    product_url=link,
                    source_url="https://www.lotteon.com/search",
                    images=[image] if image else [],
                    thumbnail=image or None,
                    rating=rating,
                    review_count=review_count,
                    review_summary=[],
                    raw_reviews_sample=[],
                    attributes={},
                )
            )

        return items

    async def search(self, query: str, filters: dict[str, Any], page_cursor: str | None, limit: int) -> dict[str, Any]:
        try:
            html = self._fetch_html(query)
            items = self._extract(html)
        except Exception:
            return {"items": [], "next_cursor": None}

        # price filter
        pr = filters.get("price_range") if isinstance(filters, dict) else None
        min_price = pr[0] if isinstance(pr, list) and len(pr) == 2 and isinstance(pr[0], int) else None
        max_price = pr[1] if isinstance(pr, list) and len(pr) == 2 and isinstance(pr[1], int) else None
        if min_price is not None or max_price is not None:
            out = []
            for it in items:
                if it.price is None:
                    out.append(it)
                    continue
                if min_price is not None and it.price < min_price:
                    continue
                if max_price is not None and it.price > max_price:
                    continue
                out.append(it)
            items = out

        start = int(page_cursor or "0")
        end = start + max(1, min(limit, 60))
        sliced = items[start:end]
        next_cursor = str(end) if end < len(items) else None
        return {"items": sliced, "next_cursor": next_cursor}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {"product_url": product_url}

    async def fetch_reviews(self, product_url: str, cursor: str | None = None, limit: int = 10) -> dict[str, Any]:
        return {"items": [], "next_cursor": None}
