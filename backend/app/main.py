from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
from fastapi import FastAPI, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import SearchRequest, MoreRequest
from app.services.search_service import SearchService
from app.services.image_llm_service import infer_style_with_gpt
from app.services.image_similarity_service import rerank_by_image_similarity

app = FastAPI(title="Clothes Search", version="0.1.0")
service = SearchService()
FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "frontend"
FRONTEND_INDEX = FRONTEND_ROOT / "index.html"
app.mount("/assets", StaticFiles(directory=FRONTEND_ROOT / "assets"), name="assets")
IMAGE_SEARCH_HISTORY = Path(__file__).resolve().parents[2] / "logs" / "image-search-history.jsonl"
DISLIKE_HISTORY = Path(__file__).resolve().parents[2] / "logs" / "image-feedback-dislike.jsonl"
LIKE_HISTORY = Path(__file__).resolve().parents[2] / "logs" / "image-feedback-like.jsonl"
CATEGORY_SYNONYMS = {
    "상의": "니트",
    "하의": "팬츠",
    "니트": "니트",
    "가디건": "가디건",
    "청바지": "데님 팬츠",
    "자켓": "자켓",
    "코트": "코트",
    "원피스": "원피스",
    "스커트": "스커트",
    "후드": "후드",
}
DISLIKED_PRODUCT_URLS: set[str] = set()
LIKED_ITEMS: dict[str, dict] = {}


def _load_dislike_history() -> None:
    if not DISLIKE_HISTORY.exists():
        return
    try:
        for line in DISLIKE_HISTORY.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            action = row.get("action")
            if action == "reset_dislike_all":
                DISLIKED_PRODUCT_URLS.clear()
                continue
            url = (row.get("product_url") or "").strip()
            if not url:
                continue
            if action == "dislike":
                DISLIKED_PRODUCT_URLS.add(url)
            elif action == "undislike":
                DISLIKED_PRODUCT_URLS.discard(url)
    except Exception:
        return


def _load_like_history() -> None:
    if not LIKE_HISTORY.exists():
        return
    try:
        for line in LIKE_HISTORY.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            action = row.get("action")
            url = (row.get("product_url") or "").strip()
            if not url:
                continue
            if action == "like":
                LIKED_ITEMS[url] = row
            elif action == "unlike":
                LIKED_ITEMS.pop(url, None)
    except Exception:
        return


_load_dislike_history()
_load_like_history()


@app.get("/")
async def index():
    return FileResponse(FRONTEND_INDEX)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _apply_dislike_filter(items: list[dict]) -> list[dict]:
    if not DISLIKED_PRODUCT_URLS:
        return items
    out = []
    for it in items:
        product_url = (it.get('product_url') or '').strip()
        if product_url and product_url in DISLIKED_PRODUCT_URLS:
            continue
        out.append(it)
    return out


def _build_relaxed_queries(tags: dict, category: str) -> list[str]:
    gender = tags.get("gender", "여자")
    color = tags.get("color", "그레이")
    pattern = tags.get("pattern", "무지")
    item = tags.get("item", "니트")
    if category and category != "auto":
        item = CATEGORY_SYNONYMS.get(category, item)

    return [
        f"{gender} {color} {pattern} {item}".strip(),
        f"{gender} {color} {item}".strip(),
        f"{color} {item}".strip(),
        f"{item}".strip(),
    ]


@app.post("/search")
async def search(req: SearchRequest):
    resp = await service.search(req)
    for r in resp.results:
        filtered = _apply_dislike_filter([it.model_dump() for it in r.items])
        r.items = [type(r.items[0])(**it) for it in filtered] if r.items else []
    return resp


@app.get("/product")
async def product(url: str = Query(..., description="product url")):
    return {
        "note": "MVP scaffold: site adapter detail fetch will be wired here.",
        "product_url": url,
    }


@app.post("/more")
async def more(req: MoreRequest):
    resp = await service.more(req)
    filtered = _apply_dislike_filter([it.model_dump() for it in resp.items])
    resp.items = [type(resp.items[0])(**it) for it in filtered] if resp.items else []
    return resp


@app.post("/image-feedback")
async def image_feedback(
    action: str = Form(...),
    product_url: str = Form(""),
    title: str = Form(""),
    brand: str = Form(""),
    price: str = Form(""),
    thumbnail: str = Form(""),
):
    ts = datetime.now(timezone.utc).isoformat()
    if action == "dislike":
        if product_url:
            DISLIKED_PRODUCT_URLS.add(product_url.strip())
        DISLIKE_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with DISLIKE_HISTORY.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": ts, "action": action, "title": title, "product_url": product_url}, ensure_ascii=False) + "\n")
    elif action == "undislike":
        if product_url:
            DISLIKED_PRODUCT_URLS.discard(product_url.strip())
        DISLIKE_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with DISLIKE_HISTORY.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": ts, "action": action, "title": title, "product_url": product_url}, ensure_ascii=False) + "\n")
    elif action == "like":
        if product_url:
            LIKED_ITEMS[product_url] = {
                "ts": ts,
                "action": "like",
                "title": title,
                "product_url": product_url,
                "brand": brand,
                "price": price,
                "thumbnail": thumbnail,
            }
            LIKE_HISTORY.parent.mkdir(parents=True, exist_ok=True)
            with LIKE_HISTORY.open("a", encoding="utf-8") as f:
                f.write(json.dumps(LIKED_ITEMS[product_url], ensure_ascii=False) + "\n")
    elif action == "unlike":
        if product_url:
            LIKED_ITEMS.pop(product_url, None)
            LIKE_HISTORY.parent.mkdir(parents=True, exist_ok=True)
            with LIKE_HISTORY.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": ts, "action": "unlike", "product_url": product_url}, ensure_ascii=False) + "\n")
    return {
        "ok": True,
        "disliked_urls": len(DISLIKED_PRODUCT_URLS),
        "liked_count": len(LIKED_ITEMS),
    }


@app.post("/image-feedback/reset-dislike")
async def reset_dislike_feedback():
    DISLIKED_PRODUCT_URLS.clear()
    DISLIKE_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with DISLIKE_HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "action": "reset_dislike_all"}, ensure_ascii=False) + "\n")
    return {"ok": True, "disliked_urls": 0}


@app.get("/liked")
async def liked_items():
    items = list(LIKED_ITEMS.values())
    items.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return {"ok": True, "items": items}


@app.get("/feedback-state")
async def feedback_state():
    return {
        "ok": True,
        "liked_urls": list(LIKED_ITEMS.keys()),
        "disliked_urls": list(DISLIKED_PRODUCT_URLS),
    }


@app.post("/image-search")
async def image_search(
    image: UploadFile = File(...),
    gender: str = Form("auto"),
    category: str = Form("auto"),
):
    data = await image.read()
    if not data:
        return {"ok": False, "error": "empty file"}

    inferred = infer_style_with_gpt(data, gender_hint=gender)
    if not inferred.get("ok"):
        return {"ok": False, "error": f"gpt_inference_failed: {inferred.get('error', 'unknown')}"}

    tags = inferred.get("tags", {})
    if category and category != "auto":
        mapped = CATEGORY_SYNONYMS.get(category, category)
        tags["item"] = mapped
        inferred["tags"] = tags

    raw_items: list[dict] = []
    chosen_query = None
    for q in _build_relaxed_queries(tags, category):
        req = SearchRequest(
            query=q,
            sites=["musinsa", "29cm", "zigzag"],
            sort="popular",
            limit_per_site=30,
            include_reviews=True,
        )
        searched = await service.search(req)
        raw_items = []
        for r in searched.results:
            for it in r.items:
                obj = it.model_dump()
                obj["site"] = r.site
                raw_items.append(obj)
        if len(raw_items) >= 8:
            chosen_query = q
            break

    if not chosen_query:
        chosen_query = _build_relaxed_queries(tags, category)[-1]

    inferred["query"] = chosen_query
    if chosen_query != _build_relaxed_queries(tags, category)[0]:
        inferred["note"] = f"{inferred.get('note', '')} (검색결과 부족으로 단계적 완화 쿼리 적용)"

    reranked = rerank_by_image_similarity(data, raw_items, top_k=60)
    reranked = _apply_dislike_filter(reranked)

    # 로컬 히스토리 저장(사용자에게는 미노출)
    IMAGE_SEARCH_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with IMAGE_SEARCH_HISTORY.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "filename": image.filename,
                    "gender": gender,
                    "category": category,
                    "query": inferred.get("query"),
                    "tags": inferred.get("tags", {}),
                    "result_count": len(reranked),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    return {
        "ok": True,
        "query": inferred["query"],
        "tags": inferred.get("tags", {}),
        "note": f"{inferred.get('note', '')} · 이미지 유사도 재정렬 적용",
        "items": reranked,
    }
