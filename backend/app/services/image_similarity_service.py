from __future__ import annotations

from io import BytesIO
from urllib.request import Request, urlopen
from typing import Any

from PIL import Image


def _image_feature(image_bytes: bytes) -> list[float]:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img = img.resize((48, 48))

    # RGB histogram (16 bins * 3 channels)
    hist = img.histogram()
    # PIL histogram for RGB is 256*3
    feat: list[float] = []
    for c in range(3):
      channel = hist[c * 256:(c + 1) * 256]
      for i in range(0, 256, 16):
          feat.append(float(sum(channel[i:i+16])))

    total = sum(feat) or 1.0
    return [v / total for v in feat]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = (sum(x * x for x in a) ** 0.5) or 1.0
    nb = (sum(y * y for y in b) ** 0.5) or 1.0
    return dot / (na * nb)


def _download_image(url: str) -> bytes | None:
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=8) as resp:
            data = resp.read()
            return data if data else None
    except Exception:
        return None


def rerank_by_image_similarity(image_bytes: bytes, items: list[dict[str, Any]], top_k: int = 60) -> list[dict[str, Any]]:
    query_feat = _image_feature(image_bytes)
    scored: list[dict[str, Any]] = []

    for it in items:
        thumb = it.get("thumbnail")
        if not thumb:
            continue
        blob = _download_image(thumb)
        if not blob:
            continue
        try:
            score = _cosine(query_feat, _image_feature(blob))
        except Exception:
            continue
        obj = dict(it)
        obj["similarity"] = round(float(score), 4)
        scored.append(obj)

    scored.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return scored[:top_k]
