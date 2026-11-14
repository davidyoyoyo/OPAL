from app.deduplication.identity import compare_records, normalize_doi, normalize_title
from app.sources.base import RawSourceItem
from app.services.research import find_duplicate_candidates, group_source_records


def item(provider: str, url: str, title: str, doi: str | None = None) -> RawSourceItem:
    return RawSourceItem(
        provider=provider,
        url=url,
        title=title,
        doi=doi,
        publication_year=2024,
        authors=["A. Researcher"],
    )


def test_doi_normalization():
    assert normalize_doi("https://doi.org/10.1234/ABC") == "10.1234/abc"


def test_title_normalization():
    assert normalize_title("The Effects of Remote-Work!") == "the effects of remote work"


def test_matching_doi_groups_mirrors_as_one_study():
    records = [
        item("catalog_a", "https://a.example/study", "Study title", "10.1234/example"),
        item("catalog_b", "https://b.example/study", "A slightly different title", "https://doi.org/10.1234/example"),
    ]
    studies = group_source_records(records)
    assert len(studies) == 1
    assert len(studies[0].locations) == 2


def test_similar_titles_are_candidates_not_automatically_merged():
    left = item("catalog_a", "https://a.example/study", "The impact of remote work on productivity")
    right = item("catalog_b", "https://b.example/study", "Impact of remote work on productivity")
    result = compare_records(left, right)
    assert result["confidence"] > 0
    assert result["same_study"] is False
    assert len(group_source_records([left, right])) == 2
    assert len(find_duplicate_candidates([left, right])) == 1
