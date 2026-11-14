import pytest

from app.sources.survey_registry import SurveySourceRegistry


class FakeSurveySource:
    name = "fake-surveys"
    description = "Test-only survey source"
    license_summary = "Test fixture"

    async def search(self, query):
        return []


def test_survey_registry_starts_empty_and_lists_sources():
    registry = SurveySourceRegistry()
    assert registry.get_all() == []
    assert registry.public_catalog() == []


def test_survey_registry_registers_independent_adapters():
    registry = SurveySourceRegistry()
    adapter = FakeSurveySource()
    registry.register(adapter)
    assert registry.get_all() == [adapter]
    assert registry.public_catalog()[0]["evidence_type"] == "measured_opinion"


def test_survey_registry_rejects_duplicate_names():
    registry = SurveySourceRegistry()
    registry.register(FakeSurveySource())
    with pytest.raises(ValueError):
        registry.register(FakeSurveySource())


def test_survey_search_reports_not_connected_without_adapters():
    import asyncio

    from app.services.survey_research import run_survey_search
    from app.sources.survey_base import SurveyQuery

    result = asyncio.run(
        run_survey_search(SurveyQuery(question="Do people support public transport?"), SurveySourceRegistry())
    )
    assert result["status"] == "not_connected"
    assert result["results"] == []


def test_survey_search_keeps_source_failures_separate():
    import asyncio

    from app.services.survey_research import run_survey_search
    from app.sources.survey_base import SurveyQuery

    class BrokenSource(FakeSurveySource):
        name = "broken-surveys"

        async def search(self, query):
            raise RuntimeError("temporary outage")

    registry = SurveySourceRegistry()
    registry.register(BrokenSource())
    result = asyncio.run(
        run_survey_search(SurveyQuery(question="Do people support public transport?"), registry)
    )
    assert result["status"] == "no_results"
    assert result["source_failures"][0]["source"] == "broken-surveys"
