from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class DiscussionQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=5, max_length=1000)
    topic: str = Field(min_length=1, max_length=240)
    limit: int = Field(default=40, ge=1, le=100)


class DiscussionRecord(BaseModel):
    """Public discussion post, kept separate from scholarly and survey records."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=500)
    platform: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=4000)
    source_url: HttpUrl
    published_at: datetime | None = None
    like_count: int | None = Field(default=None, ge=0)
    reply_count: int | None = Field(default=None, ge=0)
    repost_count: int | None = Field(default=None, ge=0)


class DiscussionSourceAdapter(Protocol):
    name: str
    description: str

    async def search(self, query: DiscussionQuery) -> list[DiscussionRecord]:
        ...
