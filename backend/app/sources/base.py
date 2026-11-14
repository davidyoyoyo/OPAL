from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class SourceQuery(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)
    language: str | None = None
    date_from: int | None = None
    date_to: int | None = None


class RawSourceItem(BaseModel):
    """Provider-neutral representation returned by any website connector."""

    provider: str
    provider_record_id: str | None = None
    url: str
    title: str
    abstract: str | None = None
    doi: str | None = None
    publication_year: int | None = None
    authors: list[str] = Field(default_factory=list)
    raw_metadata: dict = Field(default_factory=dict)


class SourceAdapter(ABC):
    """Implement this interface to add a new research website/API."""

    name: str
    description: str = ""

    @abstractmethod
    async def search(self, request: SourceQuery) -> list[RawSourceItem]:
        """Search the provider and return normalized source records."""
        raise NotImplementedError
