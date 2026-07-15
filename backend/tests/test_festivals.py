import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import create_app


def test_festivals_return_all_derived_dates() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/festivals")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 30
    assert all(item["startDate"] and item["endDate"] for item in data)
    assert all(set(item) == {
        "contentId", "title", "address", "detailAddress", "telephone", "longitude",
        "latitude", "imageUrl", "region", "startDate", "endDate",
    } for item in data)


def test_festivals_support_region_and_month_filters() -> None:
    with TestClient(create_app()) as client:
        region_response = client.get("/api/festivals", params={"region": "구미"})
        month_response = client.get("/api/festivals", params={"year": 2026, "month": 7})

    assert region_response.status_code == 200
    assert region_response.json()["data"]
    assert all(item["region"] == "구미" for item in region_response.json()["data"])
    july_ids = {item["contentId"] for item in month_response.json()["data"]}
    assert "141963" in july_ids
    assert "1801011" in july_ids


def test_festivals_reject_invalid_filters() -> None:
    with TestClient(create_app()) as client:
        month_only = client.get("/api/festivals", params={"month": 7})
        invalid_region = client.get("/api/festivals", params={"region": "서울"})
        invalid_month = client.get("/api/festivals", params={"year": 2026, "month": 13})

    assert month_only.status_code == 400
    assert invalid_region.status_code == 400
    assert invalid_month.status_code == 422


def test_derived_dates_preserve_estimated_date_provenance() -> None:
    date_file = ROOT / "data" / "derived" / "festival_dates.json"
    dates = json.loads(date_file.read_text(encoding="utf-8"))

    assert len(dates) == 30
    assert dates["3028462"]["isEstimatedDate"] is False
    assert dates["3028462"]["dateSource"] == "전국문화축제표준데이터"
    assert dates["3302702"]["isEstimatedDate"] is True
    assert dates["3302702"]["dateSource"] == "임의 생성값"


def test_openapi_contains_festival_api() -> None:
    paths = create_app().openapi()["paths"]
    assert "get" in paths["/api/festivals"]
