from __future__ import annotations

from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen
import json

from app.adapters.base import SiteAdapter
from app.schemas import ProductItem, ReviewSample


class MusinsaAdapter(SiteAdapter):
    site = "musinsa"

    def _get_json(self, url: str, referer: str = "https://www.musinsa.com/") -> dict[str, Any]:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
                "Referer": referer,
                "Origin": "https://www.musinsa.com",
            },
        )
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))

    def _summarize_reviews(self, texts: list[str]) -> list[str]:
        if not texts:
            return []

        merged = " ".join(texts)
        points: list[str] = []

        if any(k in merged for k in ["정사이즈", "오버핏", "루즈", "슬림"]):
            points.append("핏/사이즈 관련 언급이 리뷰에 반복적으로 나타남")
        if any(k in merged for k in ["부드", "촉감", "까슬", "보풀"]):
            points.append("원단 촉감/소재감에 대한 후기가 포함됨")
        if any(k in merged for k in ["봄", "얇", "두께", "가을"]):
            points.append("계절감(두께/착용시기) 관련 언급이 있음")
        if any(k in merged for k in ["비침", "밝", "아이보리"]):
            points.append("밝은 색상/비침 관련 주의 의견이 일부 있음")

        if not points:
            points.append("리뷰 원문 샘플 기반으로 추가 요약이 제한적임")
        return points[:4]

    async def search(
        self,
        query: str,
        filters: dict[str, Any],
        page_cursor: str | None,
        limit: int,
        sort: str = "popular",
    ) -> dict[str, Any]:
        page = int(page_cursor or "1")
        encoded = quote(query)
        size = max(1, min(limit, 60))
        sort_map = {
            "popular": "POPULAR",
            "rating_desc": "REVIEW",
            "review_count_desc": "REVIEW",
        }
        sort_code = sort_map.get(sort, "POPULAR")
        url = (
            "https://api.musinsa.com/api2/dp/v2/plp/goods"
            f"?gf=A&keyword={encoded}&sortCode={sort_code}&isUsed=false&page={page}&size={size}"
            "&testGroup=&seen=0&seenAds=&caller=SEARCH"
        )
        payload = self._get_json(url)
        goods = payload.get("data", {}).get("list", [])

        min_price: int | None = None
        max_price: int | None = None
        price_range = filters.get("price_range") if isinstance(filters, dict) else None
        if isinstance(price_range, list) and len(price_range) == 2:
            if isinstance(price_range[0], int):
                min_price = price_range[0]
            if isinstance(price_range[1], int):
                max_price = price_range[1]

        items: list[ProductItem] = []
        for g in goods:
            product_url = g.get("goodsLinkUrl") or f"https://www.musinsa.com/products/{g.get('goodsNo')}"
            thumb = g.get("thumbnail")
            price_value = g.get("price") if isinstance(g.get("price"), int) else None
            if min_price is not None and isinstance(price_value, int) and price_value < min_price:
                continue
            if max_price is not None and isinstance(price_value, int) and price_value > max_price:
                continue

            review_count = g.get("reviewCount")
            review_score = g.get("reviewScore")
            rating = round((float(review_score) / 20.0), 1) if isinstance(review_score, (int, float)) else None

            item = ProductItem(
                title=g.get("goodsName") or f"상품 {g.get('goodsNo')}",
                brand=g.get("brandName"),
                price=price_value,
                product_url=product_url,
                source_url=f"https://www.musinsa.com/search/goods?keyword={encoded}&gf=A",
                images=[thumb] if thumb else [],
                thumbnail=thumb,
                rating=rating,
                review_count=review_count if isinstance(review_count, int) else None,
                review_summary=[],
                raw_reviews_sample=[],
                attributes={"gender": g.get("displayGenderText")},
            )

            # 리뷰는 상위 일부만 호출해서 속도/부하 균형
            if len(items) < 8 and (review_count or 0) > 0:
                try:
                    review_url = (
                        "https://goods.musinsa.com/api2/review/v1/view/list"
                        f"?page=0&pageSize=3&goodsNo={g.get('goodsNo')}"
                        f"&sort=up_cnt_desc&selectedSimilarNo={g.get('goodsNo')}"
                        "&myFilter=false&hasPhoto=false&isExperience=false"
                    )
                    rv = self._get_json(review_url, referer=product_url)
                    rv_list = rv.get("data", {}).get("list", [])
                    texts: list[str] = []
                    for r in rv_list:
                        txt = (r.get("content") or "").strip()
                        if not txt:
                            continue
                        texts.append(txt)
                        item.raw_reviews_sample.append(
                            ReviewSample(
                                text=txt[:300],
                                meta={"date": r.get("createDate"), "grade": r.get("grade")},
                            )
                        )
                    item.review_summary = self._summarize_reviews(texts)
                except Exception:
                    pass

            items.append(item)

        page_info = payload.get("data", {}).get("pagination", {})
        has_next = bool(page_info.get("hasNext"))
        next_cursor = str(page + 1) if has_next else None
        return {"items": items, "next_cursor": next_cursor}

    async def fetch_product_detail(self, product_url: str) -> dict[str, Any]:
        return {"product_url": product_url}

    async def fetch_reviews(
        self,
        product_url: str,
        cursor: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        return {"items": [], "next_cursor": None}
