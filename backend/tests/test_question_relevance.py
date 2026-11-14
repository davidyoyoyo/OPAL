from app.services.research import classify_relevance
from app.services.synthesis import build_extractive_synthesis
from app.sources.base import RawSourceItem


def item(title: str, abstract: str) -> RawSourceItem:
    return RawSourceItem(
        provider="test",
        url="https://example.org/study",
        title=title,
        abstract=abstract,
    )


def test_prevalence_question_requires_a_reported_measure_for_direct_answer():
    study = item(
        "Consumer attitudes toward ice cream",
        "A survey of 1,200 adults found that 72% of respondents liked ice cream.",
    )

    assert classify_relevance("How many people like ice cream?", study) == "direct_answer"


def test_survey_mention_without_a_reported_quantity_is_not_a_direct_answer():
    study = item(
        "Consumer attitudes toward ice cream",
        "A survey of 1,200 respondents found that respondents generally liked ice cream.",
    )

    assert classify_relevance("How many people like ice cream?", study) is None


def test_prevalence_question_keeps_consumer_sensory_research_as_context():
    study = item(
        "Sensory acceptance of ice cream",
        "An organoleptic evaluation with 120 participants found positive responses "
        "to the flavor, aroma, and texture of ice cream.",
    )

    assert classify_relevance("How many people like ice cream?", study) == "explanatory_context"


def test_prevalence_question_rejects_topical_but_non_answering_food_science():
    study = item(
        "Development of a nutritious ice cream product",
        "This paper describes a production method using plant ingredients and "
        "compares the nutritional composition and storage stability of the product.",
    )

    assert classify_relevance("How many people like ice cream?", study) is None


def test_prevalence_synthesis_uses_explanatory_findings_not_direct_estimates_as_reasons():
    result = build_extractive_synthesis(
        "How many people like ice cream?",
        [
            {
                "id": "direct",
                "source_title": "Popularity survey",
                "source_url": "https://example.org/survey",
                "evidence_role": "direct_answer",
                "evidence_text": "A survey found that 72% of respondents liked ice cream.",
            },
            {
                "id": "context",
                "source_title": "Sensory study",
                "source_url": "https://example.org/sensory",
                "evidence_role": "explanatory_context",
                "evidence_text": (
                    "Participants rated the vanilla flavor and creamy texture highly. "
                    "The aroma was also associated with stronger liking among participants."
                ),
            },
        ],
    )

    assert result["key_points"]
    assert all(point["source_ids"] == ["context"] for point in result["key_points"])
    assert "do not tell us what percentage" in result["overview"]


def test_prevalence_fallback_does_not_turn_a_direct_measure_into_reasons():
    result = build_extractive_synthesis(
        "How many people like ice cream?",
        [{
            "id": "direct",
            "source_title": "Popularity survey",
            "source_url": "https://example.org/survey",
            "evidence_role": "direct_answer",
            "evidence_text": "A survey found that 72% of respondents liked ice cream.",
        }],
    )

    assert result["key_points"] == []
    assert "0 explanatory records" in result["overview"]
