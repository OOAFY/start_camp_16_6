import re

from openai import OpenAI, OpenAIError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.core.exceptions import OpenAIServiceError
from app.models.post import Post
from app.schemas.chat import ChatData, ChatReference, ChatRequest
from data.place_loader import load_place_dataset

SYSTEM_PROMPT = """당신은 구미·경북 지역 여행을 돕는 LocalHub 안내 챗봇입니다.
제공된 참고 정보에 근거해 한국어로 간결하고 친절하게 답하세요.
참고 정보에 없는 가격, 일정, 후기, 편의시설 등을 추측하지 마세요.
정보가 부족하면 부족하다고 명확히 말하고, 제공된 대화 기록을 고려하세요."""


def _terms(message: str) -> list[str]:
    return [term for term in re.findall(r"[가-힣A-Za-z0-9]+", message.lower()) if len(term) >= 2]


def _build_client() -> OpenAI:
    settings = load_settings()
    api_key = str(settings["openai_api_key"])
    if not api_key:
        raise OpenAIServiceError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def _build_context(places, posts) -> str:
    place_lines = [
        f"- place: {place['title']} / {place['address']} / {', '.join(place.get('tags', []))}"
        for place in places
    ]
    post_lines = [
        f"- post: {post.title} / {post.content[:500]}"
        for post in posts
    ]
    return "\n".join(place_lines + post_lines)


def create_grounded_answer(db: Session, payload: ChatRequest) -> ChatData:
    terms = _terms(payload.message)
    places = load_place_dataset()
    matched_places = [place for place in places if any(
        term in " ".join([place.get("title", ""), place.get("address", ""), " ".join(place.get("tags", []))]).lower()
        for term in terms
    )][:3]

    posts: list[Post] = []
    if terms:
        conditions = [or_(Post.title.ilike(f"%{term}%"), Post.content.ilike(f"%{term}%")) for term in terms]
        posts = list(db.scalars(select(Post).where(or_(*conditions)).order_by(Post.id.desc()).limit(3)).all())

    references = [ChatReference(type="place", id=place["contentId"], title=place["title"]) for place in matched_places]
    references += [ChatReference(type="post", id=str(post.id), title=post.title) for post in posts]
    context = _build_context(matched_places, posts) or "검색된 참고 정보 없음"
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
            max_output_tokens=600,
        )
    except OpenAIServiceError:
        raise
    except OpenAIError as exc:
        raise OpenAIServiceError("OpenAI 응답을 생성하지 못했습니다.") from exc

    answer = response.output_text.strip()
    if not answer:
        raise OpenAIServiceError("OpenAI가 빈 응답을 반환했습니다.")
    return ChatData(answer=answer, references=references)
