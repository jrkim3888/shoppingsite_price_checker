# 브라우저 릴레이 액션 시퀀스 (초안)

> 목적: 탭 배지 ON 상태에서 사이트 검색 결과를 안정적으로 추출

## 공통 시퀀스
1. 사이트 검색 URL 진입
2. 검색어 입력 + 엔터
3. 결과 리스트 로딩 대기
4. 카드 요소 반복 추출
   - title
   - product_url
   - thumbnail
   - price
   - brand (가능 시)
5. 필요 시 스크롤 2~4회 반복
6. 사이트별 limit 도달 시 종료

## Musinsa (초안)
- 검색 URL: `https://www.musinsa.com/search/goods?keyword={query}`
- 후보 셀렉터:
  - 카드: `a[href*='/products/']`, `article a[href*='/products/']`
  - 썸네일: `img[src*='msscdn']`
  - 가격: `[class*='price']`, `strong`

## 29CM (초안)
- 검색 URL: `https://shop.29cm.co.kr/search?keyword={query}`
- 후보 셀렉터:
  - 카드: `a[href*='/catalog/']`, `a[href*='/products/']`
  - 썸네일: `img`
  - 가격: `[class*='price']`

## W Concept (초안)
- 검색 URL: `https://www.wconcept.co.kr/Search?searchTerm={query}`
- 후보 셀렉터:
  - 카드: `a[href*='/Product/']`, `a[href*='/product/']`
  - 썸네일: `img`
  - 가격: `[class*='price']`

## Zigzag (초안)
- 검색 URL: `https://www.zigzag.kr/catalog/products?keyword={query}`
- 후보 셀렉터:
  - 카드: `a[href*='/catalog/products/']`, `a[href*='/products/']`
  - 썸네일: `img`
  - 가격: `[class*='price']`

## 실패 처리
- 셀렉터 미검출: 후보 셀렉터 순차 시도
- 1차 실패: 페이지 재로드 후 1회 재시도
- 2차 실패: 사이트 partial failure로 마킹하고 다음 사이트 계속
