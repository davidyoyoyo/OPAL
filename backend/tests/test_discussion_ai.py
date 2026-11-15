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
