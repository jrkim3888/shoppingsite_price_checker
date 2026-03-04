from __future__ import annotations

from io import BytesIO
from PIL import Image


def _hsv_of_pixel(r: int, g: int, b: int) -> tuple[float, float, float]:
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(rf, gf, bf), min(rf, gf, bf)
    diff = mx - mn

    # hue
    if diff == 0:
        h = 0.0
    elif mx == rf:
        h = (60 * ((gf - bf) / diff) + 360) % 360
    elif mx == gf:
        h = (60 * ((bf - rf) / diff) + 120) % 360
    else:
        h = (60 * ((rf - gf) / diff) + 240) % 360

    s = 0.0 if mx == 0 else diff / mx
    v = mx
    return h, s, v


def _dominant_color_name(image: Image.Image) -> str:
    # Downsample + quantize for stable dominant color extraction
    small = image.convert("RGB").resize((80, 80))
    pixels = list(small.getdata())

    color_bins: dict[str, int] = {}
    for r, g, b in pixels:
        h, s, v = _hsv_of_pixel(r, g, b)

        # very dark / very bright / desaturated first
        if v < 0.15:
            label = "블랙"
        elif v > 0.9 and s < 0.12:
            label = "화이트"
        elif s < 0.18:
            label = "그레이"
        else:
            if 0 <= h < 18 or 340 <= h <= 360:
                label = "빨간색"
            elif 18 <= h < 38:
                label = "주황"
            elif 38 <= h < 65:
                label = "노란색"
            elif 65 <= h < 165:
                label = "초록"
            elif 165 <= h < 250:
                label = "파란색"
            elif 250 <= h < 290:
                label = "보라"
            elif 290 <= h < 340:
                label = "핑크"
            else:
                label = "그레이"

        color_bins[label] = color_bins.get(label, 0) + 1

    # Bias correction: if gray barely wins over a strong chromatic color, pick chromatic
    sorted_bins = sorted(color_bins.items(), key=lambda x: x[1], reverse=True)
    top_label, top_count = sorted_bins[0]
    if top_label == "그레이":
        for label, cnt in sorted_bins[1:]:
            if label not in {"화이트", "블랙", "그레이"} and cnt >= top_count * 0.75:
                return label
    return top_label


def _infer_item_from_filename(filename: str) -> str:
    name = (filename or "").lower()
    table = {
        "cardigan": "가디건",
        "hood": "후드",
        "zip": "집업",
        "coat": "코트",
        "jacket": "자켓",
        "skirt": "스커트",
        "dress": "원피스",
        "shirt": "셔츠",
        "tee": "티셔츠",
        "knit": "니트",
        "sweater": "니트",
        "가디건": "가디건",
        "니트": "니트",
        "원피스": "원피스",
        "스커트": "스커트",
        "자켓": "자켓",
        "코트": "코트",
    }
    for key, value in table.items():
        if key in name:
            return value
    return "니트"


def _infer_gender(filename: str) -> str:
    name = (filename or "").lower()
    female_keys = ["woman", "women", "female", "girl", "여자", "여성", "우먼"]
    male_keys = ["man", "men", "male", "boy", "남자", "남성", "맨"]

    if any(k in name for k in female_keys):
        return "여자"
    if any(k in name for k in male_keys):
        return "남자"
    return "여자"


def _infer_pattern(image: Image.Image) -> str:
    gray = image.convert("L").resize((96, 96))
    px = gray.load()
    w, h = gray.size

    # Edge / stripe style heuristic
    diff_x = 0
    diff_y = 0
    for y in range(h):
        for x in range(w - 1):
            diff_x += abs(px[x + 1, y] - px[x, y])
    for y in range(h - 1):
        for x in range(w):
            diff_y += abs(px[x, y + 1] - px[x, y])

    # Block variance heuristic for pattern richness
    block = 12
    means: list[float] = []
    for by in range(0, h, block):
        for bx in range(0, w, block):
            vals = []
            for y in range(by, min(by + block, h)):
                for x in range(bx, min(bx + block, w)):
                    vals.append(px[x, y])
            if vals:
                means.append(sum(vals) / len(vals))

    if not means:
        return "무지"

    mean_all = sum(means) / len(means)
    var = sum((m - mean_all) ** 2 for m in means) / len(means)

    # thresholds tuned for rough MVP behavior
    if var < 120:
        return "무지"
    if diff_x > diff_y * 1.25:
        return "세로 패턴"
    if diff_y > diff_x * 1.25:
        return "가로 패턴"
    if var > 800:
        return "체크/패턴"
    return "패턴"


def infer_style_from_image(image_bytes: bytes, filename: str | None = None, gender_hint: str = "auto") -> dict:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    color = _dominant_color_name(image)
    item = _infer_item_from_filename(filename or "")
    if gender_hint in {"여자", "남자", "공용"}:
        gender = gender_hint
    else:
        gender = _infer_gender(filename or "")
    pattern = _infer_pattern(image)

    query = f"{gender} {color} {pattern} {item}"
    return {
        "query": query,
        "tags": {
            "gender": gender,
            "color": color,
            "pattern": pattern,
            "item": item,
            "season": "봄",
        },
        "note": "MVP 추론(색상/패턴 휴리스틱 + 파일명 키워드)입니다. 고급 비전모델보다 정확도는 낮을 수 있어요.",
    }
