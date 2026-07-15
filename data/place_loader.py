from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

RAW_DIR = Path(__file__).resolve().parent / "raw"
DERIVED_DIR = Path(__file__).resolve().parent / "derived"
ALLOWED_REGIONS = {"구미", "대구", "칠곡", "성주", "고령"}
CONTENT_TYPE_MAP = {
    "관광지": "관광지",
    "문화시설": "문화시설",
    "축제공연행사": "축제공연행사",
    "여행코스": "여행코스",
    "레포츠": "레포츠",
    "숙박": "숙박",
    "쇼핑": "쇼핑",
    "음식점": "음식점",
}


def _load_raw_files() -> List[Dict[str, Any]]:
    files = sorted(RAW_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError("No raw JSON files found under data/raw")

    combined: List[Dict[str, Any]] = []
    seen_content_ids: set[str] = set()
    for path in files:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        items = payload.get("items", [])
        if isinstance(items, dict):
            items = [items]

        for item in items:
            if not isinstance(item, dict):
                continue
            content_id = str(item.get("contentid") or "")
            if content_id and content_id in seen_content_ids:
                continue
            if content_id:
                seen_content_ids.add(content_id)
            combined.append({
                "sourceFile": path.name,
                "contentType": payload.get("contentType") or item.get("contenttypeid") or "",
                "contentTypeId": payload.get("contentTypeId") or item.get("contenttypeid") or "",
                **item,
            })

    return combined


def _read_derived_tags() -> Dict[str, List[str]]:
    tag_file = DERIVED_DIR / "place_tags.json"
    if not tag_file.exists():
        return {}

    with tag_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        return {}

    result: Dict[str, List[str]] = {}
    for content_id, tags in data.items():
        if isinstance(tags, list):
            result[str(content_id)] = [str(tag) for tag in tags if str(tag)]
    return result


def _normalize_region(addr1: str) -> str:
    value = (addr1 or "").strip()
    if not value:
        return ""
    for region in sorted(ALLOWED_REGIONS, key=len, reverse=True):
        if region in value:
            return region
    return ""


def _safe_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_place(raw_item: Dict[str, Any], derived_tags: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
    content_id = str(raw_item.get("contentid") or "")
    addr1 = str(raw_item.get("addr1") or "")
    addr2 = str(raw_item.get("addr2") or "")
    telephone = str(raw_item.get("tel") or "")
    image_url = str(raw_item.get("firstimage") or "")
    thumbnail_url = str(raw_item.get("firstimage2") or "")
    content_type = str(raw_item.get("contentType") or raw_item.get("contenttypeid") or "")
    region = _normalize_region(addr1)
    tags = []
    if derived_tags:
        tags = derived_tags.get(content_id, [])

    return {
        "contentId": content_id,
        "contentTypeId": str(raw_item.get("contenttypeid") or ""),
        "contentType": content_type,
        "title": str(raw_item.get("title") or ""),
        "address": addr1,
        "detailAddress": addr2,
        "telephone": telephone,
        "longitude": _safe_float(raw_item.get("mapx")),
        "latitude": _safe_float(raw_item.get("mapy")),
        "imageUrl": image_url,
        "thumbnailUrl": thumbnail_url,
        "region": region,
        "tags": tags,
    }


def load_place_dataset() -> List[Dict[str, Any]]:
    raw_items = _load_raw_files()
    derived_tags = _read_derived_tags()
    places = [normalize_place(item, derived_tags) for item in raw_items]
    return places


def filter_places(
    places: List[Dict[str, Any]],
    *,
    content_type: Optional[str] = None,
    region: Optional[str] = None,
    keyword: Optional[str] = None,
) -> List[Dict[str, Any]]:
    keyword_normalized = (keyword or "").strip().lower()
    filtered = places
    if content_type:
        filtered = [place for place in filtered if place.get("contentType") == content_type]
    if region:
        filtered = [place for place in filtered if place.get("region") == region]
    if keyword_normalized:
        filtered = [
            place for place in filtered
            if keyword_normalized in (place.get("title") or "").lower()
            or keyword_normalized in (place.get("address") or "").lower()
        ]
    return filtered


def get_place_by_id(places: List[Dict[str, Any]], content_id: str) -> Optional[Dict[str, Any]]:
    for place in places:
        if place.get("contentId") == str(content_id):
            return place
    return None
