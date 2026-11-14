from app.db.models import Base


def test_all_core_tables_are_registered():
    expected = {
        "source_providers", "research_works", "source_records", "surveys",
        "survey_waves", "survey_questions", "stance_categories",
        "answer_options", "response_distributions", "qualitative_findings",
        "argument_themes", "finding_argument_themes", "extraction_runs",
        "data_provenance",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_schema_stores_aggregate_distributions_not_respondents():
    assert "response_distributions" in Base.metadata.tables
    assert not any("respondent" in name.lower() for name in Base.metadata.tables)


def test_original_and_english_text_are_separate():
    work = Base.metadata.tables["research_works"].c
    question = Base.metadata.tables["survey_questions"].c
    assert {"title_original", "title_language", "title_english"}.issubset(work.keys())
    assert {"question_text_original", "question_language", "question_text_english"}.issubset(question.keys())


def test_waves_are_distinct_from_study_version_history():
    assert "survey_waves" in Base.metadata.tables
    assert not any("version" in name.lower() for name in Base.metadata.tables)


def test_question_denominator_and_both_percentage_values_are_supported():
    columns = Base.metadata.tables["response_distributions"].c
    assert {"base_n", "reported_percentage", "calculated_percentage", "response_count"}.issubset(columns.keys())
