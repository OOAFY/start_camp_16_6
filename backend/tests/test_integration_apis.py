from pathlib import Path
import sys

from fastapi.testclient import TestClient
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import create_app
from app.core.config import load_settings
from app.services import chat as chat_service


def test_travel_test_questions_hide_scoring_metadata() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/travel-test/questions")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["version"] == "1.0"
    assert data["requiredAnswerCount"] == 5
    assert len(data["questions"]) == 5
    option = data["questions"][0]["options"][0]
    assert set(option) == {"optionId", "text"}
    assert "scores" not in response.text
    assert "primaryType" not in response.text


def test_places_list_detail_and_not_found() -> None:
    with TestClient(create_app()) as client:
        listing = client.get("/api/places", params={"page": 1, "size": 2, "region": "구미"})
        assert listing.status_code == 200
        body = listing.json()["data"]
        assert len(body["items"]) <= 2
        assert body["totalPages"] >= 1
        place = body["items"][0]
        detail = client.get(f"/api/places/{place['contentId']}")
        assert detail.status_code == 200
        assert detail.json()["data"] == place
        assert client.get("/api/places/not-found").status_code == 404


def test_chat_calls_gpt_5_mini_with_place_references(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                output_text="모델이 생성한 여행 답변",
                status="completed",
                incomplete_details=None,
                usage=SimpleNamespace(
                    output_tokens=20,
                    output_tokens_details=SimpleNamespace(reasoning_tokens=5),
                ),
            )

    class FakeOpenAI:
        def __init__(self, api_key: str):
            captured["api_key"] = api_key
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    monkeypatch.setattr(chat_service, "OpenAI", FakeOpenAI)
    load_settings.cache_clear()

    try:
        with TestClient(create_app()) as client:
            place = client.get("/api/places", params={"region": "구미", "size": 1}).json()["data"]["items"][0]
            response = client.post(
                "/api/chat",
                json={
                    "message": f"{place['title']} 정보를 알려줘",
                    "history": [{"role": "user", "content": "가족 여행이야"}],
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["answer"] == "모델이 생성한 여행 답변"
        assert any(ref["type"] == "place" and ref["id"] == place["contentId"] for ref in data["references"])
        assert captured["model"] == "gpt-5-mini"
        assert captured["reasoning"] == {"effort": "minimal"}
        assert captured["max_output_tokens"] == 3000
        assert captured["input"][0] == {"role": "user", "content": "가족 여행이야"}
        assert "참고 정보:" in captured["input"][-1]["content"]
    finally:
        load_settings.cache_clear()


def test_chat_finds_july_gumi_festivals_from_natural_language(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                output_text="7월 구미 축제 안내",
                status="completed",
                incomplete_details=None,
                usage=SimpleNamespace(
                    output_tokens=20,
                    output_tokens_details=SimpleNamespace(reasoning_tokens=5),
                ),
            )

    class FakeOpenAI:
        def __init__(self, api_key: str):
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(chat_service, "OpenAI", FakeOpenAI)
    load_settings.cache_clear()

    try:
        with TestClient(create_app()) as client:
            expected = client.get(
                "/api/festivals",
                params={"year": 2026, "month": 7},
            ).json()["data"]
            response = client.post(
                "/api/chat",
                json={"message": "7월에 있는 구미의 축제 몇 가지 알려줘", "history": []},
            )

        assert response.status_code == 200
        references = response.json()["data"]["references"]
        festival_ids = {item["id"] for item in references if item["type"] == "festival"}
        assert festival_ids == {item["contentId"] for item in expected[:5]}
        context = captured["input"][-1]["content"]
        assert "정확히 일치하는 축제 없음: 지역=구미, 월=7" in context
        assert "festival:" in context
        assert all(item["title"] in context for item in expected[:5])
    finally:
        load_settings.cache_clear()


def test_chat_returns_openai_api_error_without_api_key(monkeypatch) -> None:
    # 로컬 .env가 있어도 빈 프로세스 환경변수가 우선하도록 테스트를 격리합니다.
    monkeypatch.setenv("OPENAI_API_KEY", "")
    load_settings.cache_clear()

    try:
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            response = client.post("/api/chat", json={"message": "여행지를 추천해줘", "history": []})

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "OPENAI_API_ERROR"
    finally:
        load_settings.cache_clear()


def test_chat_reports_output_token_exhaustion(monkeypatch) -> None:
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                output_text="",
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
                usage=SimpleNamespace(
                    output_tokens=3000,
                    output_tokens_details=SimpleNamespace(reasoning_tokens=3000),
                ),
            )

    class FakeOpenAI:
        def __init__(self, api_key: str):
            assert api_key == "test-key"
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(chat_service, "OpenAI", FakeOpenAI)
    load_settings.cache_clear()

    try:
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            response = client.post("/api/chat", json={"message": "가족 축제를 추천해줘", "history": []})

        assert response.status_code == 500
        assert response.json()["error"] == {
            "code": "OPENAI_API_ERROR",
            "detail": "OpenAI 응답 생성 토큰이 부족합니다.",
        }
    finally:
        load_settings.cache_clear()


def test_travel_test_returns_type_and_recommendations() -> None:
    payload = {"answers": [
        {"questionId": 1, "optionId": "Q1_A"}, {"questionId": 2, "optionId": "Q2_C"},
        {"questionId": 3, "optionId": "Q3_A"}, {"questionId": 4, "optionId": "Q4_B"},
        {"questionId": 5, "optionId": "Q5_D"},
    ]}
    with TestClient(create_app()) as client:
        response = client.post("/api/travel-test", json=payload)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["travelType"]["code"] == "HEALING"
        assert data["travelType"]["description"]
        assert len(data["recommendations"]) <= 3
        assert all("matchScore" in item for item in data["recommendations"])


def test_travel_test_rejects_duplicate_question() -> None:
    payload = {"answers": [{"questionId": 1, "optionId": "Q1_A"}] * 5}
    with TestClient(create_app()) as client:
        response = client.post("/api/travel-test", json=payload)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_REQUEST"
