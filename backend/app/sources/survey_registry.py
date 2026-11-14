from app.sources.survey_base import SurveySourceAdapter


class SurveySourceRegistry:
    """Independent registry for question-level survey repositories."""

    def __init__(self) -> None:
        self._adapters: dict[str, SurveySourceAdapter] = {}

    def register(self, adapter: SurveySourceAdapter) -> None:
        key = adapter.name.strip().lower()
        if not key:
            raise ValueError("A survey source adapter must have a name.")
        if key in self._adapters:
            raise ValueError(f"Survey source '{key}' is already registered.")
        self._adapters[key] = adapter

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
