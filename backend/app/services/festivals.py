import calendar
import json
from datetime import date
from pathlib import Path

from fastapi import HTTPException

from app.schemas.festival import Festival
from data.place_loader import ALLOWED_REGIONS, load_place_dataset


DATE_FILE = Path(__file__).resolve().parents[3] / "data" / "derived" / "festival_dates.json"


def _load_dates() -> dict[str, dict]:
    try:
        payload = json.loads(DATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="축제 날짜 데이터를 불러올 수 없습니다.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="축제 날짜 데이터 구조가 올바르지 않습니다.")
    return payload


def _parse_date(value: object, content_id: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"축제 {content_id}의 날짜가 올바르지 않습니다.") from exc


def list_festivals(region: str | None = None, year: int | None = None, month: int | None = None) -> list[Festival]:
    if region not in (None, "", "all") and region not in ALLOWED_REGIONS:
        raise HTTPException(status_code=400, detail="지역이 올바르지 않습니다.")
    if month is not None and year is None:
        raise HTTPException(status_code=400, detail="월 필터에는 연도가 필요합니다.")

    dates = _load_dates()
    unique_places: dict[str, dict] = {}
    try:
        for place in load_place_dataset():
            if place.get("contentType") == "축제공연행사":
                unique_places.setdefault(str(place["contentId"]), place)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="축제 데이터를 불러올 수 없습니다.") from exc

    period_start = period_end = None
    if year is not None:
        period_start = date(year, month or 1, 1)
        last_month = month or 12
        period_end = date(year, last_month, calendar.monthrange(year, last_month)[1])

    festivals: list[Festival] = []
    for content_id, place in unique_places.items():
        date_config = dates.get(content_id)
        if not isinstance(date_config, dict):
            continue
        start_date = _parse_date(date_config.get("startDate"), content_id)
        end_date = _parse_date(date_config.get("endDate"), content_id)
        if end_date < start_date:
            raise HTTPException(status_code=500, detail=f"축제 {content_id}의 날짜 범위가 올바르지 않습니다.")
        if region not in (None, "", "all") and place.get("region") != region:
            continue
        if period_start and period_end and (end_date < period_start or start_date > period_end):
            continue
        festivals.append(Festival(
            content_id=content_id,
            title=place.get("title", ""),
            address=place.get("address", ""),
            detail_address=place.get("detailAddress", ""),
            telephone=place.get("telephone", ""),
            longitude=place.get("longitude"),
            latitude=place.get("latitude"),
            image_url=place.get("imageUrl", ""),
            region=place.get("region", ""),
            start_date=start_date,
            end_date=end_date,
        ))

    return sorted(festivals, key=lambda item: (item.start_date, item.content_id))
