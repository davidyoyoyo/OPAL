from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.models.survey import SurveyQuestionResult


class SurveyQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=5, max_length=1000)
    population: str | None = Field(default=None, max_length=500)
    geography: str | None = Field(default=None, max_length=200)
    time_period: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=20, ge=1, le=100)


class SurveySourceAdapter(Protocol):
    """Connector contract for archives that expose original survey question data."""

    name: str
    description: str
    license_summary: str

    async def search(self, query: SurveyQuery) -> list[SurveyQuestionResult]:
        ...
