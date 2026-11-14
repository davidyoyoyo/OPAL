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
