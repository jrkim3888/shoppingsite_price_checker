from __future__ import annotations

from collections import OrderedDict
from uuid import uuid4
from datetime import datetime, timezone
import inspect

from app.adapters.mock_adapter import MockAdapter
from app.adapters.musinsa_adapter import MusinsaAdapter
from app.adapters.twentyninecm_adapter import TwentyNineCmAdapter
from app.adapters.wconcept_adapter import WConceptAdapter
from app.adapters.zigzag_adapter import ZigzagAdapter
from app.adapters.brandi_adapter import BrandiAdapter
from app.adapters.hiver_adapter import HiverAdapter
from app.adapters.ably_adapter import AblyAdapter
from app.adapters.ssf_adapter import SsfAdapter
from app.adapters.lotteon_adapter import LotteOnAdapter
from app.adapters.elevenst_adapter import ElevenStAdapter
from app.schemas import SearchRequest, SearchResponse, SiteResult, MoreRequest, MoreResponse


def _normalize_keywords(query: str) -> list[str]:
    return [w.strip() for w in query.replace(",", " ").split() if w.strip()]


class SearchService:
    def __init__(self) -> None:
        self._adapter_factory = {
            "musinsa": lambda: MusinsaAdapter(),
            "29cm": lambda: TwentyNineCmAdapter(),
            "wconcept": lambda: WConceptAdapter(),
            "zigzag": lambda: ZigzagAdapter(),
            "brandi": lambda: BrandiAdapter(),
            "hiver": lambda: HiverAdapter(),
            "ably": lambda: AblyAdapter(),
            "ssf": lambda: SsfAdapter(),
            "lotteon": lambda: LotteOnAdapter(),
            "11st": lambda: ElevenStAdapter(),
        }

    async def search(self, req: SearchRequest) -> SearchResponse:
        normalized = {
            "keywords": _normalize_keywords(req.query),
            "inferred_filters": req.filters.model_dump(),
        }

        site_results: list[SiteResult] = []
        pagination: dict[str, dict[str, str | None]] = {}

        for site in req.sites:
            adapter = self._adapter_factory[site]()
            search_kwargs = {
                "query": req.query,
                "filters": req.filters.model_dump(),
                "page_cursor": None,
                "limit": req.limit_per_site,
            }
            if "sort" in inspect.signature(adapter.search).parameters:
                search_kwargs["sort"] = req.sort
            page = await adapter.search(**search_kwargs)

            # URL dedupe within each site
            dedup = OrderedDict()
            for item in page["items"]:
                dedup[item.product_url] = item

            items = list(dedup.values())
            site_results.append(SiteResult(site=site, items=items))
            pagination[site] = {"next": page.get("next_cursor")}

        return SearchResponse(
            request_id=str(uuid4()),
            normalized_query=normalized,
            results=site_results,
            pagination=pagination,
            generated_at=datetime.now(timezone.utc),
        )

    async def more(self, req: MoreRequest) -> MoreResponse:
        if not req.cursor or req.cursor.lower() == "none":
            return MoreResponse(site=req.site, items=[], next_cursor=None)

        adapter = self._adapter_factory[req.site]()
        search_kwargs = {
            "query": req.query,
            "filters": req.filters.model_dump(),
            "page_cursor": req.cursor,
            "limit": req.limit_per_site,
        }
        if "sort" in inspect.signature(adapter.search).parameters:
            search_kwargs["sort"] = req.sort
        page = await adapter.search(**search_kwargs)

        dedup = OrderedDict()
        for item in page.get("items", []):
            dedup[item.product_url] = item

        return MoreResponse(
            site=req.site,
            items=list(dedup.values()),
            next_cursor=page.get("next_cursor"),
        )
