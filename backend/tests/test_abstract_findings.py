from app.models.evidence import SourceLocation, StudyRecord
from app.services.research import extract_abstract_findings


def study(abstract: str | None) -> StudyRecord:
    return StudyRecord(
        title="Public attitudes toward renewable energy",
        publication_year=2024,
        doi="10.1000/example",
        abstract=abstract,
        locations=[
            SourceLocation(
                provider="crossref",
                url="https://doi.org/10.1000/example",
            )
        ],
    )


def test_extracts_traceable_passage_from_abstract():
    record = study(
        "<jats:sec><jats:title>Results</jats:title>"
        "<jats:p>Most respondents supported renewable energy policy in the survey.</jats:p>"
        "</jats:sec>"
    )
    findings = extract_abstract_findings("renewable energy policy", [record])

    assert len(findings) == 1
    assert "Most respondents supported renewable energy policy" in findings[0]["evidence_text"]
    assert findings[0]["source_title"] == record.title
    assert findings[0]["source_url"] == "https://doi.org/10.1000/example"
    assert findings[0]["evidence_level"] == "abstract"
    assert "not an independently verified survey result" in findings[0]["interpretation"]


def test_skips_missing_or_too_short_abstracts():
    assert extract_abstract_findings("renewable energy", [study(None)]) == []
    assert extract_abstract_findings("renewable energy", [study("Short text.")]) == []
