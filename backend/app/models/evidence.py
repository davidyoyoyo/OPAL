from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


EvidenceKind = Literal["survey", "discussion", "supporting_research"]


class SourceLocation(BaseModel):
    """A website/page where a study or evidence item was found."""

    provider: str
    url: HttpUrl
    retrieved_at: date | None = None
    provider_record_id: str | None = None


class StudyRecord(BaseModel):
    """The underlying research work, independent of the websites hosting it."""

    title: str
    publication_year: int | None = None
    doi: str | None = None
    identifiers: dict[str, str] = Field(default_factory=dict)
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    locations: list[SourceLocation] = Field(default_factory=list)
    identity_status: Literal["verified", "probable", "unresolved"] = "unresolved"


class EvidenceRecord(BaseModel):
    """An extracted finding. Never treat a study mirror as a new independent study."""

    evidence_kind: EvidenceKind
    claim_or_theme: str
    study: StudyRecord | None = None
    population: str | None = None
    geography: str | None = None
    fieldwork_start: date | None = None
    fieldwork_end: date | None = None
    sample_size: int | None = Field(default=None, ge=1)
    value: float | None = None
    unit: str | None = None
    methodology_note: str | None = None
    source_url: HttpUrl
