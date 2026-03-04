# SiteAdapter 템플릿 (실구현용)

```python
class SiteAdapter(ABC):
    site: str

    async def search(self, query: str, filters: dict, page_cursor: str | None, limit: int) -> dict:
        ...

    async def fetch_product_detail(self, product_url: str) -> dict:
        ...

    async def fetch_reviews(self, product_url: str, cursor: str | None = None, limit: int = 10) -> dict:
        ...
```

## 구현 규칙
- 반환 필드는 `backend/app/schemas.py`의 `ProductItem` 최소 스키마를 충족.
- `source_url`은 검색 결과 페이지 또는 상세 페이지의 실제 URL 사용.
- 리뷰 요약은 샘플 텍스트가 있는 경우에만 생성.
- 사이트 오류는 예외 전파 대신 `{items: [], next_cursor: None, error: "..."}`로 반환.

## 정규화 규칙
- price: 정수 KRW
- rating: 0~5 float
- review_count: 정수
- images: 중복 제거 + 썸네일 우선
- dedupe key: `product_url`
