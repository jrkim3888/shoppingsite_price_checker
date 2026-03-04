from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

SiteName = Literal["musinsa", "29cm", "wconcept", "zigzag", "brandi", "hiver", "ably", "ssf", "lotteon", "11st"]


class SearchFilters(BaseModel):
    season: str | None = None
    category: str | None = None
    mood: list[str] = Field(default_factory=list)
    price_range: list[int] | None = None
    color: list[str] = Field(default_factory=list)
    shipping: str | None = None


class SearchRequest(BaseModel):
    query: str
    sites: list[SiteName] = Field(default_factory=lambda: ["musinsa", "29cm", "wconcept", "zigzag"])
    limit_per_site: int = 50
    sort: str = "popular"
    filters: SearchFilters = Field(default_factory=SearchFilters)
    language: str = "ko"
    image_count_prefer: str = "many"
    include_reviews: bool = True


class ReviewSample(BaseModel):
    text: str
    meta: dict[str, Any] = Field(default_factory=dict)


class ProductItem(BaseModel):
    title: str
    brand: str | None = None
    price: int | None = None
    currency: str = "KRW"
    product_url: str
    source_url: str
    images: list[str] = Field(default_factory=list)
    thumbnail: str | None = None
    rating: float | None = None
    review_count: int | None = None
    review_summary: list[str] = Field(default_factory=list)
    raw_reviews_sample: list[ReviewSample] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class SiteResult(BaseModel):
    site: SiteName
    items: list[ProductItem] = Field(default_factory=list)


class SearchResponse(BaseModel):
    request_id: str
    normalized_query: dict[str, Any]
    results: list[SiteResult]
    pagination: dict[str, dict[str, Any]] = Field(default_factory=dict)
    generated_at: datetime


class MoreRequest(BaseModel):
    site: SiteName
    query: str
    cursor: str
    limit_per_site: int = 50
    sort: str = "popular"
    filters: SearchFilters = Field(default_factory=SearchFilters)


class MoreResponse(BaseModel):
    site: SiteName
    items: list[ProductItem] = Field(default_factory=list)
    next_cursor: str | None = None
