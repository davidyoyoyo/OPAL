from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


ResponseCategory = Literal[
    "support", "oppose", "neutral", "mixed", "undecided",
    "dont_know", "no_opinion", "other", "unclassified"
]


class SurveyResponse(BaseModel):
    """One original answer option from a published survey question."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=300)
    normalized_category: ResponseCategory = "unclassified"
    count: int | None = Field(default=None, ge=0)
    percentage: float | None = Field(default=None, ge=0, le=100)
    percentage_method: Literal["source_reported", "calculated", "not_reported"] = "not_reported"

    @model_validator(mode="after")
    def validate_percentage_provenance(self):
        if self.count is None and self.percentage is None:
            raise ValueError("A response must include a count or a percentage.")
        if self.percentage_method == "calculated" and (self.count is None or self.percentage is None):
            raise ValueError("Calculated percentages require an original response count and a calculated value.")
        if self.percentage_method == "source_reported" and self.percentage is None:
            raise ValueError("Source-reported percentages must include the reported percentage.")
        if self.percentage_method == "not_reported" and self.percentage is not None:
            raise ValueError("A percentage must be marked source_reported or calculated.")
        return self


class SurveyQuestionResult(BaseModel):
    """Question-level survey data with denominator and provenance preserved."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=300)
    question_text: str = Field(min_length=5, max_length=3000)
    source_name: str = Field(min_length=1, max_length=200)
    source_title: str = Field(min_length=1, max_length=500)
    source_url: HttpUrl
    dataset_id: str = Field(min_length=1, max_length=300)
    survey_wave: str | None = Field(default=None, max_length=200)
    population: str | None = Field(default=None, max_length=500)
    geography: str | None = Field(default=None, max_length=200)
    sample_size: int | None = Field(default=None, ge=1)
    base_n: int | None = Field(default=None, ge=1)
    base_description: str | None = Field(default=None, max_length=1000)
    fieldwork_start: date | None = None
    fieldwork_end: date | None = None
    weighting_note: str | None = Field(default=None, max_length=1500)
    distribution_complete: bool = False
    responses: list[SurveyResponse] = Field(min_length=2, max_length=100)

    @model_validator(mode="after")
    def validate_question_metadata(self):
        if self.sample_size is not None and self.base_n is not None and self.base_n > self.sample_size:
            raise ValueError("Question base cannot exceed the total sample size.")
        if self.base_n is None and any(response.percentage is not None for response in self.responses):
            raise ValueError("Percentages require the denominator for this exact survey question.")
        if self.fieldwork_start and self.fieldwork_end and self.fieldwork_start > self.fieldwork_end:
            raise ValueError("Fieldwork start cannot be after fieldwork end.")
        if self.base_n is not None:
            for response in self.responses:
                if response.count is not None and response.count > self.base_n:
                    raise ValueError("A response count cannot exceed the question-specific base.")
                if response.percentage_method == "calculated":
                    expected = round((response.count / self.base_n) * 100, 1)
                    if response.percentage is None or abs(response.percentage - expected) > 0.11:
                        raise ValueError("Calculated percentage does not match count / question base.")

        if self.distribution_complete:
            if any(response.percentage is None for response in self.responses):
                raise ValueError("A complete distribution requires a percentage for every response option.")
            total = sum(response.percentage or 0 for response in self.responses)
            if abs(total - 100.0) > 1.5:
                raise ValueError("A complete response distribution must sum to approximately 100%.")
        return self


def calculate_response_percentage(count: int, base_n: int) -> float:
    """Calculate a percentage only from a known question-level denominator."""
    if count < 0:
        raise ValueError("Response count cannot be negative.")
    if base_n <= 0:
        raise ValueError("Question base must be positive.")
    if count > base_n:
        raise ValueError("Response count cannot exceed the question-specific base.")
    return round((count / base_n) * 100, 1)
