from __future__ import annotations

import base64
import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


PROMPT = """
너는 패션 이미지 분석기다.
입력 이미지를 보고 JSON 객체만 출력하라.

규칙:
- 키워드는 최대한 간결하게 (한 단어/짧은 구)
- 과장 금지, 보이는 것만 추론

필드:
- gender: 여자 | 남자 | 공용
- color: 한국어 단일 색상명 (예: 빨간색, 파란색, 블랙, 화이트, 베이지, 그레이)
- pattern: 무지 | 가로 패턴 | 세로 패턴 | 체크 | 스트라이프 | 도트 | 기타
- item: 니트 | 가디건 | 자켓 | 코트 | 셔츠 | 티셔츠 | 원피스 | 스커트 | 팬츠 | 후드 | 기타
- style_tags: 한국어 짧은 태그 배열(최대 2개, 각 태그 1~2단어)
- confidence: 0~1 float

반드시 JSON 객체만 반환.
""".strip()


def infer_style_with_gpt(image_bytes: bytes, gender_hint: str = "auto") -> dict[str, Any]:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"ok": False, "error": "OPENAI_API_KEY missing"}

    client = OpenAI(api_key=api_key)
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    hint = ""
    if gender_hint in {"여자", "남자", "공용"}:
        hint = f"성별 힌트: {gender_hint}. 가능한 한 이 값을 우선 반영하라."

    def _ask(extra_rule: str = "") -> dict[str, Any]:
        resp = client.responses.create(
            model="gpt-5.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT + "\n" + hint + "\n" + extra_rule},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
                    ],
                }
            ],
            temperature=0,
        )

        text = getattr(resp, "output_text", "") or ""
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    try:
        data = _ask()
    except Exception as e:
        return {"ok": False, "error": f"invalid_json: {e}"}

    item = data.get("item") or "니트"
    if item == "기타":
        try:
            data = _ask("item은 기타를 쓰지 말고, 가장 가까운 카테고리 하나를 반드시 선택하라.")
            item = data.get("item") or "니트"
        except Exception:
            item = "니트"

    gender = data.get("gender") or "여자"
    color = data.get("color") or "그레이"
    pattern = data.get("pattern") or "무지"
    tags = data.get("style_tags") or []
    confidence = data.get("confidence")

    query = f"{gender} {color} {pattern} {item}"

    return {
        "ok": True,
        "query": query,
        "tags": {
            "gender": gender,
            "color": color,
            "pattern": pattern,
            "item": item,
            "style_tags": tags,
            "confidence": confidence,
        },
        "note": "GPT 비전 모델 기반 키워드 추론 결과",
    }
