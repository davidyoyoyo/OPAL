from app.services.research import is_relevant, relevance_score
from app.sources.base import RawSourceItem


def item(title: str, abstract: str | None = None) -> RawSourceItem:
    return RawSourceItem(
        provider="test",
        url="https://example.org/study",
        title=title,
        abstract=abstract,
    )


def test_relevant_title_is_kept():
    study = item("Public attitudes toward renewable energy in Romania")
    assert is_relevant("What do people think about renewable energy?", study)


def test_unrelated_title_and_abstract_are_excluded():
    study = item(
        "A new method for classifying marine bacteria",
        "This paper studies bacterial genomes and ocean ecosystems.",
    )
    assert not is_relevant("Public opinion about renewable energy", study)


def test_abstract_can_support_relevance_when_multiple_topic_terms_match():
    study = item(
        "A national survey",
        "The report examines renewable energy policy and public attitudes.",
    )
    assert is_relevant("Public attitudes toward renewable energy policy", study)


def test_relevance_score_is_higher_for_matching_title():
    relevant = item("Public attitudes toward renewable energy")
    unrelated = item("A study of marine bacteria")
    assert relevance_score("Public opinion about renewable energy", relevant) > relevance_score(
        "Public opinion about renewable energy", unrelated
    )
