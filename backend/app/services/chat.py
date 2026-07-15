import logging
import re

from openai import OpenAI, OpenAIError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.core.exceptions import OpenAIServiceError
from app.models.post import Post
from app.schemas.chat import ChatData, ChatReference, ChatRequest
from app.schemas.festival import Festival
from app.services.festivals import list_festivals
from data.place_loader import ALLOWED_REGIONS
from data.place_loader import load_place_dataset

SYSTEM_PROMPT = """당신은 구미·경북 지역 여행을 돕는 LocalHub 안내 챗봇입니다.
제공된 참고 정보에 근거해 한국어로 간결하고 친절하게 답하세요.
참고 정보에 없는 가격, 일정, 후기, 편의시설 등을 추측하지 마세요.
정보가 부족하면 부족하다고 명확히 말하고, 제공된 대화 기록을 고려하세요."""

logger = logging.getLogger(__name__)


def _terms(message: str) -> list[str]:
    return [term for term in re.findall(r"[가-힣A-Za-z0-9]+", message.lower()) if len(term) >= 2]


def _build_client() -> OpenAI:
    settings = load_settings()
    api_key = str(settings["openai_api_key"])
    if not api_key:
        raise OpenAIServiceError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def _find_festivals(message: str) -> tuple[list[Festival], str | None]:
    """질문 속 지역·연·월을 해석해 정제된 축제 일정에서 후보를 찾습니다."""
    if "축제" not in message:
        return [], None

    region = next((value for value in ALLOWED_REGIONS if value in message), None)
    year_match = re.search(r"(\d{4})\s*년", message)
    month_match = re.search(r"(?<!\d)(1[0-2]|0?[1-9])\s*월", message)
    year = int(year_match.group(1)) if year_match else None
    month = int(month_match.group(1)) if month_match else None

    def search(search_region: str | None) -> list[Festival]:
        if year is not None:
            return list_festivals(region=search_region, year=year, month=month)
        results = list_festivals(region=search_region)
        if month is not None:
            results = [
                festival for festival in results
                if festival.start_date.month <= month <= festival.end_date.month
            ]
        return results

    festivals = search(region)
    if festivals or region is None or month is None:
        return festivals[:5], None

    alternatives = search(None)
    notice = (
        f"요청 조건과 정확히 일치하는 축제 없음: 지역={region}, 월={month}. "
        "아래 축제는 같은 달의 다른 지원 지역 일정이므로 대안으로만 안내할 것."
    )
    return alternatives[:5], notice


def _build_context(places, posts, festivals: list[Festival], festival_notice: str | None) -> str:
    place_lines = [
        f"- place: {place['title']} / {place['address']} / {', '.join(place.get('tags', []))}"
        for place in places
    ]
    post_lines = [
        f"- post: {post.title} / {post.content[:500]}"
        for post in posts
    ]
    festival_lines = [
        f"- festival: {festival.title} / {festival.region} / {festival.address} / "
        f"{festival.start_date.isoformat()}~{festival.end_date.isoformat()}"
        for festival in festivals
    ]
    notice_lines = [f"- festival_search_notice: {festival_notice}"] if festival_notice else []
    return "\n".join(notice_lines + festival_lines + place_lines + post_lines)


def create_grounded_answer(db: Session, payload: ChatRequest) -> ChatData:
    terms = _terms(payload.message)
    places = load_place_dataset()
    festivals, festival_notice = _find_festivals(payload.message)
    festival_ids = {festival.content_id for festival in festivals}
    matched_places = [place for place in places if any(
        term in " ".join([place.get("title", ""), place.get("address", ""), " ".join(place.get("tags", []))]).lower()
        for term in terms
    ) and place.get("contentId") not in festival_ids][:3]

    posts: list[Post] = []
    if terms:
        conditions = [or_(Post.title.ilike(f"%{term}%"), Post.content.ilike(f"%{term}%")) for term in terms]
        posts = list(db.scalars(select(Post).where(or_(*conditions)).order_by(Post.id.desc()).limit(3)).all())

    references = [
        ChatReference(type="festival", id=festival.content_id, title=festival.title)
        for festival in festivals
    ]
    references += [ChatReference(type="place", id=place["contentId"], title=place["title"]) for place in matched_places]
    references += [ChatReference(type="post", id=str(post.id), title=post.title) for post in posts]
    context = _build_context(matched_places, posts, festivals, festival_notice) or "검색된 참고 정보 없음"
    messages = [
        {"role": item.role, "content": item.content}
        for item in payload.history[-10:]
    ]
    messages.append({
        "role": "user",
        "content": f"참고 정보:\n{context}\n\n사용자 질문:\n{payload.message}",
    })

    settings = load_settings()
    try:
        response = _build_client().responses.create(
            model=str(settings["openai_model"]),
            instructions=SYSTEM_PROMPT,
            input=messages,
            reasoning={"effort": "minimal"},
            max_output_tokens=3000,
        )
    except OpenAIServiceError:
        raise
    except OpenAIError as exc:
        raise OpenAIServiceError("OpenAI 응답을 생성하지 못했습니다.") from exc

    incomplete_reason = getattr(response.incomplete_details, "reason", None)
    usage = getattr(response, "usage", None)
    output_details = getattr(usage, "output_tokens_details", None)
    logger.info(
        "OpenAI response status=%s reason=%s output_tokens=%s reasoning_tokens=%s",
        response.status,
        incomplete_reason,
        getattr(usage, "output_tokens", None),
        getattr(output_details, "reasoning_tokens", None),
    )

    if response.status == "incomplete":
        if incomplete_reason == "max_output_tokens":
            raise OpenAIServiceError("OpenAI 응답 생성 토큰이 부족합니다.")
        if incomplete_reason == "content_filter":
            raise OpenAIServiceError("OpenAI 콘텐츠 필터로 응답이 중단되었습니다.")
        raise OpenAIServiceError("OpenAI 응답 생성이 완료되지 않았습니다.")

    answer = response.output_text.strip()
    if not answer:
        raise OpenAIServiceError("OpenAI가 빈 응답을 반환했습니다.")
    return ChatData(answer=answer, references=references)
