from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel


class ChatHistoryItem(CamelModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(CamelModel):
    message: str = Field(min_length=1)
    history: list[ChatHistoryItem] = Field(default_factory=list)


class ChatReference(CamelModel):
    type: Literal["place", "post", "festival"]
    id: str
    title: str


class ChatData(CamelModel):
    answer: str
    references: list[ChatReference]
