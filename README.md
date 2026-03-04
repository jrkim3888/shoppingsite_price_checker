# fashion-finder (MVP scaffold)

여성 의류 사이트 통합 검색/이미지 갤러리 프로젝트의 초기 골격입니다.
https://github.com/atgs6591/shoppingmall_test 사이트 fork

## 현재 상태(팩트)
- FastAPI 백엔드 골격 생성
- `/search`, `/product`, `/more`, `/health` 엔드포인트 생성
- SiteAdapter 인터페이스 + mock adapter 생성
- 결과 스키마는 요청한 JSON 구조를 반영

## 아직 미구현
- 실제 무신사/29CM/W컨셉/지그재그 크롤러
- 브라우저 릴레이 연동 액션 실행기
- 리뷰 실수집/요약
- 프론트엔드 UI

## 실행
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

## 다음 단계 제안
1. `SiteAdapter`별 실제 구현 (우선 1개 사이트)
2. 리뷰/이미지 지연 로딩 API 구현
3. 프론트 그리드 UI(검색 + 더보기)
4. 브라우저 릴레이 fallback 플로우 연결
