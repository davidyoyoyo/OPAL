from app.sources.survey_base import SurveySourceAdapter


class SurveySourceRegistry:
    """Independent registry for question-level survey repositories."""

    def __init__(self) -> None:
        self._adapters: dict[str, SurveySourceAdapter] = {}

    def register(self, adapter: SurveySourceAdapter) -> None:
        if adapter.name in self._adapters:
            raise ValueError(f"Survey source '{adapter.name}' is already registered.")
        self._adapters[adapter.name] = adapter

    def get_all(self) -> list[SurveySourceAdapter]:
        return list(self._adapters.values())

    def public_catalog(self) -> list[dict[str, str]]:
        return [
            {
                "name": adapter.name,
                "description": adapter.description,
                "license_summary": adapter.license_summary,
                "evidence_type": "measured_opinion",
            }
            for adapter in self._adapters.values()
        ]


survey_registry = SurveySourceRegistry()
