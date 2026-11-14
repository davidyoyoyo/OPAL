from datetime import date

import pytest
from pydantic import ValidationError

from app.models.survey import (
    SurveyQuestionResult,
    SurveyResponse,
    calculate_response_percentage,
)


def response(label: str, count: int, percentage: float) -> SurveyResponse:
    return SurveyResponse(
        label=label,
        count=count,
        percentage=percentage,
        percentage_method="source_reported",
    )


def valid_survey(**overrides):
    values = {
        "id": "survey-1-question-3",
        "question_text": "How satisfied are you with public transport?",
        "source_name": "Example Survey Archive",
        "source_title": "Public Transport Attitudes 2025",
        "source_url": "https://example.org/survey/1",
        "dataset_id": "dataset-1",
        "population": "Adults aged 18+",
        "geography": "Example country",
        "sample_size": 1000,
        "base_n": 900,
        "fieldwork_start": date(2025, 1, 1),
        "fieldwork_end": date(2025, 1, 20),
        "distribution_complete": True,
        "responses": [
            response("Very satisfied", 450, 50.0),
            response("Not very satisfied", 270, 30.0),
            response("Not at all satisfied", 180, 20.0),
        ],
    }
    values.update(overrides)
    return SurveyQuestionResult(**values)


def test_accepts_question_level_survey_distribution():
    survey = valid_survey()
    assert survey.base_n == 900
    assert sum(item.percentage for item in survey.responses) == 100.0


def test_rejects_missing_original_question_wording():
    with pytest.raises(ValidationError):
        valid_survey(question_text="")


def test_rejects_base_larger_than_sample():
    with pytest.raises(ValidationError):
        valid_survey(base_n=1100)


def test_rejects_incomplete_distribution_marked_complete():
    with pytest.raises(ValidationError):
        valid_survey(responses=[
            response("Very satisfied", 450, 50.0),
            response("Not very satisfied", 270, 30.0),
        ])


def test_percentage_is_calculated_from_question_base_not_total_sample():
    assert calculate_response_percentage(450, 900) == 50.0
    assert calculate_response_percentage(450, 1000) == 45.0


def test_calculated_percentage_requires_a_count():
    with pytest.raises(ValidationError):
        SurveyResponse(
            label="Support",
            percentage=50.0,
            percentage_method="calculated",
        )


def test_rejects_percentages_without_question_specific_base():
    with pytest.raises(ValidationError):
        valid_survey(
            base_n=None,
            responses=[
                response("Support", 450, 50.0),
                response("Oppose", 450, 50.0),
            ],
        )


def test_rejects_incorrectly_calculated_percentage():
    with pytest.raises(ValidationError):
        valid_survey(
            responses=[
                SurveyResponse(
                    label="Support",
                    count=450,
                    percentage=45.0,
                    percentage_method="calculated",
                ),
                response("Oppose", 450, 50.0),
            ],
        )
