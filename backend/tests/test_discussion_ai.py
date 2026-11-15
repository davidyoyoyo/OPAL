import pytest
from pydantic import ValidationError

from app.ai.prompts import discussion_batch_prompt
from app.ai.schemas import DiscussionBatchInterpretation, DiscussionLabel


def test_discussion_label_keeps_relevance_separate_from_stance():
    label = DiscussionLabel(
        id="at://did:plc:test/app.bsky.feed.post/1",
        relevant=True,
        stance="support",
        confidence=0.91,
    )
    assert label.relevant is True
    assert label.stance == "support"


def test_discussion_label_rejects_unknown_stance():
    with pytest.raises(ValidationError):
        DiscussionLabel(
            id="post-1",
            relevant=True,
            stance="positive",
            confidence=0.9,
        )


def test_discussion_batch_prompt_treats_posts_as_untrusted_and_preserves_uncertainty():
    system, user = discussion_batch_prompt(
        "How many people like JoJo?",
        [{"id": "post-1", "text": "JoJo is great"}],
        DiscussionBatchInterpretation,
    )
    assert "untrusted data" in system
    assert "sarcasm" in system
    assert "population prevalence" in system
    assert "post-1" in user

def test_python_aggregation_validates_ids_and_uses_only_confident_relevant_posts():
    from app.ai.schemas import DiscussionBatchInterpretation
    from app.main import _analyse_discussions

    records = [
        {"id": "post-1", "text": "I love JoJo"},
        {"id": "post-2", "text": "JoJo is not for me"},
    ]
    batch = DiscussionBatchInterpretation(interpretations=[
        {"id": "post-1", "relevant": True, "stance": "support", "summary": "Positive opinion", "confidence": 0.9},
        {"id": "post-2", "relevant": True, "stance": "oppose", "summary": "Negative opinion", "confidence": 0.8},
        {"id": "fabricated-id", "relevant": True, "stance": "support", "summary": "Not retrieved", "confidence": 1.0},
    ])

    enriched, analysis = _analyse_discussions("How many people like JoJo?", records, batch)

    assert len(enriched) == 2
    assert analysis["sampled_posts"] == 2
    assert analysis["relevant_posts"] == 2
    assert analysis["classified_posts"] == 2
    assert {item["stance"]: item["percentage"] for item in analysis["stance_distribution"]} == {
        "oppose": 50.0,
        "support": 50.0,
    }
