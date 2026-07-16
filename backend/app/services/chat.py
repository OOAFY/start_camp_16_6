import logging
import re
from datetime import date

from openai import OpenAI, OpenAIError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.core.exceptions import OpenAIServiceError
from app.models.post import Post
from app.schemas.chat import ChatData, ChatReference, ChatRequest
from app.schemas.festival import Festival
from app.services.festivals import list_festivals
from data.place_loader import ALLOWED_REGIONS
from data.place_loader import load_place_dataset
from data.travel_recommender import load_travel_types

SYSTEM_PROMPT = """당신은 구미·경북 지역 여행을 돕는 LocalHub 안내 챗봇입니다.
제공된 참고 정보에 근거해 한국어로 간결하고 친절하게 답하세요.
참고 정보에 없는 가격, 일정, 후기, 편의시설 등을 추측하지 마세요.
커뮤니티 게시글은 작성자의 경험과 추천으로 구분해 요약하고 게시글 제목을 함께 안내하세요.
지도 또는 축제 캘린더 질문에는 답변 아래의 관련 링크를 누르면 해당 화면으로 이동할 수 있다고 안내하세요.
여행 성향이 제공되면 사용자의 명시 조건을 지키면서 성향 키워드와 태그가 맞는 장소를 우선 안내하고, 일치 태그를 추천 이유에 반영하세요.
여행 성향이 제공된 경우 성향 정보가 없다고 말하거나 성향을 다시 질문하지 마세요.
여행 성향이 없더라도 검색된 장소가 있으면 일반 여행지 관점에서 최대 3곳을 먼저 추천하고, 취향 테스트 권유는 마지막 한 문장으로만 안내하세요. 번호가 붙은 추가 질문 선택지는 나열하지 마세요.
정보가 부족하면 부족하다고 명확히 말하고, 제공된 대화 기록을 고려하세요."""

logger = logging.getLogger(__name__)

COMMUNITY_INTENT_WORDS = {
    "커뮤니티", "게시글", "후기", "이용자", "사람들", "작성된", "추천한", "소개한",
}
POST_STOP_WORDS = {
    "구미", "경북", "커뮤니티", "게시글", "글", "이용자", "사람들", "관련된", "관련",
    "추천", "추천한", "소개한", "찾아줘", "알려줘", "있는지", "있어", "어디야", "어떤",
    "내용", "요약해", "작성된", "가볼", "만한", "관한", "장소", "여행지",
}
POST_TERM_GROUPS = (
    {"아이", "어린이", "가족", "자녀", "키즈", "체험"},
    {"맛집", "음식", "먹거리", "식당", "시장", "전통시장"},
    {"데이트", "연인", "커플", "코스"},
    {"산책", "걷기", "둘레길", "공원", "트레킹"},
    {"주말", "나들이", "여행", "여행후기"},
    {"후기", "다녀온", "방문", "경험"},
    {"축제", "행사", "공연"},
)
POST_CATEGORIES = {
    "맛집": {"맛집", "음식", "먹거리", "식당", "시장", "전통시장"},
    "축제": {"축제", "행사", "공연"},
    "생활": {"생활", "육아"},
    "자유": {"자유"},
    "여행": {"여행", "여행지", "후기", "산책", "데이트", "주말", "나들이", "아이", "가족"},
}
PLACE_STOP_WORDS = {
    "지도", "지도에서", "위치", "좌표", "장소", "여행지", "명소", "주변", "근처",
    "보여줘", "알려줘", "찾아줘", "열어줘", "보고", "싶어", "몇", "여러", "추천한",
    "추천해줘", "추천", "가기", "가고", "갈", "좋은", "만한", "어디에", "어디야",
    "나한테", "나에게", "내게", "나를", "좋을만한", "어울리는", "맞는", "괜찮은",
}
PLACE_TERM_GROUPS = (
    {"아이", "어린이", "가족", "자녀", "키즈", "체험"},
    {"맛집", "음식", "음식점", "먹거리", "식당", "시장"},
    {"산책", "걷기", "둘레길", "공원", "트레킹"},
    {"데이트", "연인", "커플", "코스"},
    {"관광지", "명소", "여행", "여행지"},
)


def _terms(message: str) -> list[str]:
    return [term for term in re.findall(r"[가-힣A-Za-z0-9]+", message.lower()) if len(term) >= 2]


def _normalize_post_term(term: str) -> str:
    normalized = term.lower()
    for suffix in ("에서", "에게", "으로", "들의", "와", "과", "을", "를", "은", "는", "이", "가", "에", "의", "도"):
        if normalized.endswith(suffix) and len(normalized) > len(suffix) + 1:
            return normalized[:-len(suffix)]
    return normalized


def _is_community_question(message: str) -> bool:
    normalized_terms = {_normalize_post_term(term) for term in _terms(message)}
    return bool(normalized_terms & COMMUNITY_INTENT_WORDS)


def _post_search_terms(message: str) -> tuple[set[str], set[str]]:
    original_terms = {
        normalized
        for term in _terms(message)
        if len(normalized := _normalize_post_term(term)) >= 2 and normalized not in POST_STOP_WORDS
    }
    expanded_terms = set(original_terms)
    for group in POST_TERM_GROUPS:
        if original_terms & group:
            expanded_terms.update(group)
    return original_terms, expanded_terms


def _post_category(message: str) -> str | None:
    normalized_terms = {_normalize_post_term(term) for term in _terms(message)}
    for category, keywords in POST_CATEGORIES.items():
        if normalized_terms & keywords:
            return category
    return None


def _travel_preference(travel_type: str | None) -> dict | None:
    if not travel_type:
        return None
    config = load_travel_types().get(travel_type)
    if not config:
        return None
    return {"code": travel_type, **config}


def _is_generic_travel_recommendation(message: str) -> bool:
    compact_message = re.sub(r"\s+", "", message)
    return "추천" in compact_message and any(term in compact_message for term in (
        "여행지", "장소", "가볼만한곳", "갈만한곳", "명소",
    ))


def _find_places(
    places: list[dict],
    message: str,
    excluded_ids: set[str],
    travel_type: str | None = None,
    limit: int = 3,
) -> list[dict]:
    original_terms = {
        normalized
        for term in _terms(message)
        if len(normalized := _normalize_post_term(term)) >= 2 and normalized not in PLACE_STOP_WORDS
    }
    expanded_terms = set(original_terms)
    for group in PLACE_TERM_GROUPS:
        if original_terms & group:
            expanded_terms.update(group)

    preference = _travel_preference(travel_type)
    preference_keywords = [keyword.lower() for keyword in preference["keywords"]] if preference else []
    ranked: list[tuple[int, int, dict]] = []
    for place in places:
        if place.get("contentId") in excluded_ids:
            continue
        title = str(place.get("title", "")).lower()
        address = str(place.get("address", "")).lower()
        region = str(place.get("region", "")).lower()
        content_type = str(place.get("contentType", "")).lower()
        tags = " ".join(place.get("tags", [])).lower()
        score = 0
        for term in expanded_terms:
            weight = 2 if term in original_terms else 1
            if term in title:
                score += 6 * weight
            if term in tags:
                score += 4 * weight
            if term in content_type:
                score += 3 * weight
            if term in region:
                score += 2 * weight
            if term in address:
                score += weight
        preference_score = sum(
            1
            for tag in place.get("tags", [])
            if any(keyword in tag.lower() or tag.lower() in keyword for keyword in preference_keywords)
        )
        if any(keyword in content_type for keyword in preference_keywords):
            preference_score += 1

        # 질문 조건이 있으면 일치 후보 안에서 성향으로 정렬하고, 조건이 없으면 성향 태그 자체로 후보를 만듭니다.
        if score > 0 or (not original_terms and preference_score > 0):
            ranked.append((score + preference_score * 4, preference_score, place))

    if preference is None and _is_generic_travel_recommendation(message):
        travel_content_types = {"관광지", "문화시설", "레포츠"}
        travel_candidates = [item for item in ranked if item[2].get("contentType") in travel_content_types]
        if travel_candidates:
            ranked = travel_candidates

    ranked.sort(key=lambda item: (item[0], item[1], item[2].get("title", "")), reverse=True)
    return [place for _, _, place in ranked[:limit]]


def _is_recommendation_ranking_question(message: str) -> bool:
    """게시글 내용 추천이 아니라 DB 추천 수 순위를 묻는 질문인지 판별합니다."""
    compact_message = re.sub(r"\s+", "", message)
    recommendation_count_terms = ("추천수", "추천횟수", "추천개수", "추천건수")
    ranking_terms = ("가장", "제일", "최고", "높은", "많은", "1위", "인기")
    return (
        any(term in compact_message for term in recommendation_count_terms)
        and any(term in compact_message for term in ranking_terms)
    )


def _find_posts(db: Session, message: str, limit: int = 5) -> list[Post]:
    original_terms, expanded_terms = _post_search_terms(message)
    category = _post_category(message) if _is_community_question(message) else None
    recommendation_ranking_intent = _is_recommendation_ranking_question(message)

    query = select(Post)
    if category:
        query = query.where(Post.category == category)
    candidates = list(db.scalars(query.order_by(Post.id.desc()).limit(200)).all())

    ranked: list[tuple[int, Post]] = []
    for post in candidates:
        title = post.title.lower()
        content = post.content.lower()
        score = 4 if category and post.category == category else 0
        for term in expanded_terms:
            weight = 2 if term in original_terms else 1
            if term in title:
                score += 4 * weight
            if term in content:
                score += weight
        # 추천 수 순위 질문은 제목·본문 키워드와 무관하게 모든 후보를 정렬해야 합니다.
        if score > 0 or not expanded_terms or recommendation_ranking_intent:
            ranked.append((score, post))

    recent_intent = "최근" in message or "최신" in message
    if recent_intent:
        ranked.sort(key=lambda item: (item[1].created_at, item[0], item[1].id), reverse=True)
    elif recommendation_ranking_intent:
        ranked.sort(
            key=lambda item: (item[1].recommendation_count, item[0], item[1].created_at, item[1].id),
            reverse=True,
        )
    else:
        ranked.sort(
            key=lambda item: (item[0], item[1].recommendation_count, item[1].created_at, item[1].id),
            reverse=True,
        )
    result_limit = 1 if recommendation_ranking_intent else limit
    return [post for _, post in ranked[:result_limit]]


def _build_client() -> OpenAI:
    settings = load_settings()
    api_key = str(settings["openai_api_key"])
    if not api_key:
        raise OpenAIServiceError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def _today() -> date:
    return date.today()


def _is_map_question(message: str) -> bool:
    compact_message = re.sub(r"\s+", "", message)
    return any(term in compact_message for term in (
        "지도", "위치", "어디에", "좌표", "지도에서", "지도열어", "지도보여",
    ))


def _is_festival_question(message: str) -> bool:
    return any(term in message for term in ("축제", "행사", "이벤트", "캘린더", "달력"))


def _is_calendar_question(message: str) -> bool:
    return any(term in message for term in ("캘린더", "달력", "일정표"))


def _festival_period(message: str) -> tuple[int, int] | None:
    """명시 연·월과 '이번 달/다음 달'을 캘린더 이동에 사용할 연·월로 변환합니다."""
    today = _today()
    compact_message = re.sub(r"\s+", "", message)
    if "다음달" in compact_message:
        return (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    if "이번달" in compact_message or "이달" in compact_message:
        return today.year, today.month

    year_match = re.search(r"(\d{4})\s*년", message)
    month_match = re.search(r"(?<!\d)(1[0-2]|0?[1-9])\s*월", message)
    if not month_match:
        return None
    return (int(year_match.group(1)) if year_match else today.year, int(month_match.group(1)))


def _find_festivals(message: str) -> tuple[list[Festival], str | None]:
    """질문 속 지역·연·월을 해석해 정제된 축제 일정에서 후보를 찾습니다."""
    if not _is_festival_question(message):
        return [], None

    region = next((value for value in ALLOWED_REGIONS if value in message), None)
    period = _festival_period(message)
    year, month = period if period else (None, None)
    upcoming_intent = any(phrase in message for phrase in (
        "가장 가까운", "가까운 시일", "다가오는", "다음 축제",
        "예정된 축제", "지금 날짜", "현재 기준", "오늘 기준",
    ))
    requested_count = 1 if re.search(r"(?:하나|한\s*개|1\s*개)", message) else 5

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
    if upcoming_intent and year is None and month is None:
        today = _today()
        festivals = [festival for festival in festivals if festival.end_date >= today]
        festivals.sort(key=lambda festival: (max(festival.start_date, today), festival.end_date, festival.content_id))
        notice = (
            f"기준일={today.isoformat()}. 기준일에 진행 중이거나 이후에 시작하는 축제를 대상으로 "
            "가장 가까운 일정 순으로 정렬했음."
        )
        return festivals[:requested_count], notice

    if festivals or region is None or month is None:
        return festivals[:requested_count], None

    alternatives = search(None)
    notice = (
        f"요청 조건과 정확히 일치하는 축제 없음: 지역={region}, 월={month}. "
        "아래 축제는 같은 달의 다른 지원 지역 일정이므로 대안으로만 안내할 것."
    )
    return alternatives[:requested_count], notice


def _build_context(
    places,
    posts,
    festivals: list[Festival],
    festival_notice: str | None,
    travel_preference: dict | None,
) -> str:
    preference_keywords = travel_preference["keywords"] if travel_preference else []
    preference_lines = []
    if travel_preference:
        preference_lines.append(
            f"- travel_preference: code={travel_preference['code']} / name={travel_preference['name']} / "
            f"keywords={', '.join(preference_keywords)}"
        )
    place_lines = [
        f"- place: {place['title']} / {place['address']} / tags={', '.join(place.get('tags', []))} / "
        f"preference_matches={', '.join(tag for tag in place.get('tags', []) if any(keyword in tag or tag in keyword for keyword in preference_keywords)) or '없음'}"
        for place in places
    ]
    post_lines = [
        f"- post: id={post.id} / category={post.category} / recommendations={post.recommendation_count} / "
        f"created={post.created_at.isoformat()} / title={post.title} / content={post.content[:500]}"
        for post in posts
    ]
    festival_lines = [
        f"- festival: {festival.title} / {festival.region} / {festival.address} / "
        f"{festival.start_date.isoformat()}~{festival.end_date.isoformat()}"
        for festival in festivals
    ]
    notice_lines = [f"- festival_search_notice: {festival_notice}"] if festival_notice else []
    return "\n".join(preference_lines + notice_lines + festival_lines + place_lines + post_lines)


def create_grounded_answer(db: Session, payload: ChatRequest) -> ChatData:
    places = load_place_dataset()
    travel_preference = _travel_preference(payload.travel_type)
    festivals, festival_notice = _find_festivals(payload.message)
    festival_ids = {festival.content_id for festival in festivals}
    map_intent = _is_map_question(payload.message)
    if _is_festival_question(payload.message) and not map_intent:
        matched_places = []
    else:
        matched_places = _find_places(
            places,
            payload.message,
            set() if map_intent else festival_ids,
            travel_type=payload.travel_type,
        )

    posts = _find_posts(db, payload.message)

    calendar_references: list[ChatReference] = []
    if _is_calendar_question(payload.message):
        period = _festival_period(payload.message)
        if period is None and festivals:
            period = (festivals[0].start_date.year, festivals[0].start_date.month)
        if period is None:
            today = _today()
            period = (today.year, today.month)
        year, month = period
        calendar_references.append(ChatReference(
            type="festival_calendar",
            id=f"{year:04d}-{month:02d}",
            title=f"{year}년 {month}월 축제 캘린더",
        ))

    references = calendar_references + [
        ChatReference(type="festival", id=festival.content_id, title=festival.title)
        for festival in festivals
    ]
    place_reference_type = "map" if map_intent else "place"
    references += [
        ChatReference(type=place_reference_type, id=place["contentId"], title=place["title"])
        for place in matched_places
    ]
    references += [ChatReference(type="post", id=str(post.id), title=post.title) for post in posts]
    context = _build_context(
        matched_places,
        posts,
        festivals,
        festival_notice,
        travel_preference,
    ) or "검색된 참고 정보 없음"
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
