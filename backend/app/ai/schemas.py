from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResearchPlan(BaseModel):
    """A structured interpretation of what a research question is asking."""

    model_config = ConfigDict(extra="forbid")

    intent: Literal[
        "prevalence", "comparison", "trend", "explanation",
        "qualitative_themes", "general_research", "unknown"
    ]
    topic: str = Field(min_length=1, max_length=240)
    population: str | None = Field(default=None, max_length=240)
    geography: str | None = Field(default=None, max_length=160)
    time_period: str | None = Field(default=None, max_length=160)
    requested_measures: list[str] = Field(default_factory=list, max_length=12)
    preferred_evidence: list[Literal[
        "representative_survey", "survey", "qualitative_opinion",
        "scholarly_research", "official_statistics", "news_context"
    ]] = Field(default_factory=list, max_length=8)
    clarification_needed: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)
    uncertainty_notes: list[str] = Field(default_factory=list, max_length=8)


class EvidenceInterpretation(BaseModel):
    """AI labels an evidence passage; it does not certify its truth or representativeness."""

    model_config = ConfigDict(extra="forbid")

    evidence_type: Literal[
        "survey_result", "qualitative_opinion", "research_finding",
        "contextual_information", "irrelevant", "unclear"
    ]
    topic: str | None = Field(default=None, max_length=240)
    stance: Literal[
        "support", "oppose", "neutral", "mixed", "undecided",
        "dont_know", "no_opinion", "not_applicable", "unclear"
    ] = "not_applicable"
    sentiment: Literal["positive", "negative", "neutral", "mixed", "unclear"] = "unclear"
    population: str | None = Field(default=None, max_length=240)
    geography: str | None = Field(default=None, max_length=160)
    fieldwork_period: str | None = Field(default=None, max_length=160)
    sample_size: int | None = Field(default=None, ge=0)
    percentage: float | None = Field(default=None, ge=0, le=100)
    exact_evidence_quote: str | None = Field(default=None, max_length=1200)
    summary: str = Field(default="", max_length=700)
    missing_information: list[str] = Field(default_factory=list, max_length=12)
    confidence: float = Field(ge=0, le=1)


class DiscussionLabel(BaseModel):
    """One AI interpretation of a public discussion post."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=500)
    relevant: bool
    stance: Literal["support", "oppose", "neutral", "mixed", "unclear"]
    summary: str = Field(default="", max_length=240)
    confidence: float = Field(ge=0, le=1)


class DiscussionBatchInterpretation(BaseModel):
    """Bounded batch response; Python validates IDs and calculates sample counts."""

    model_config = ConfigDict(extra="forbid")

    interpretations: list[DiscussionLabel] = Field(max_length=50)


class AIInterpretationError(RuntimeError):
    """Raised when AI is unavailable or returns invalid structured output."""
