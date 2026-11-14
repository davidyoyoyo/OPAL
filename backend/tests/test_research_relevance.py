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


def test_medical_treatment_choice_is_not_relevant_to_ivy_league_university_choice():
    study = item(
        "What matters most to patients with severe aortic stenosis when choosing treatment?",
        "Adults and caregivers discussed treatment decisions and shared decision making.",
    )
    assert not is_relevant(
        "What matters most when choosing an ivy league university?",
        study,
    )


def test_ice_cream_melting_paper_is_not_preference_survey_evidence():
    study = item(
        "How many universes are necessary for an ice cream to melt?",
        "We investigate the thermodynamic properties of black holes and entropy.",
    )
    assert not is_relevant("How many people like ice cream?", study)


def test_university_choice_research_is_kept():
    study = item(
        "Factors influencing university choice among prospective students",
        "The study examines criteria and decisions used when selecting a university.",
    )
    assert is_relevant(
        "What matters most when choosing an ivy league university?",
        study,
    )
