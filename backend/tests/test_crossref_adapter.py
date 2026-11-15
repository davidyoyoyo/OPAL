from app.sources.providers.crossref import CrossrefAdapter


def test_crossref_query_removes_question_framing_for_niche_topics():
    assert CrossrefAdapter.build_topic_query("How many people like JoJo?") == "jojo"


def test_crossref_query_preserves_multiword_topic():
    assert CrossrefAdapter.build_topic_query("What do people think about renewable energy?") == "renewable energy"


def test_crossref_query_falls_back_for_empty_cleaned_query():
    assert CrossrefAdapter.build_topic_query("How many?") == "How many?"
