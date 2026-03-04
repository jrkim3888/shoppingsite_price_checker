# UI 와이어프레임 / 컴포넌트 구조

## 레이아웃
- Header: 검색창 + 사이트 토글 + 검색 버튼
- Sidebar: 필터(가격/색상/무드/카테고리)
- Main: 카드 그리드 + 더보기 버튼
- Detail Modal: 추가 이미지 / 리뷰 요약 / 원문 링크

## 컴포넌트
- `SearchBar`
- `SiteToggle`
- `FilterPanel`
- `ResultGrid`
- `ProductCard`
- `ProductDetailModal`
- `PaginationBar`

## 카드 표시 필드
- 썸네일
- 사이트명
- 상품명
- 가격
- 평점/리뷰수(있을 때)
- 리뷰요약(최대 3줄)
- 버튼: 원문 보기 / 상세 보기

## 상태
- idle / loading / partial-error / done
- 사이트별 에러 배지 표시(예: zigzag 수집 실패)
