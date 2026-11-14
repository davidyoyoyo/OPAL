import asyncio

from app.models.survey import SurveyQuestionResult
from app.sources.survey_base import SurveyQuery
from app.sources.survey_registry import SurveySourceRegistry


async def run_survey_search(query: SurveyQuery, registry: SurveySourceRegistry) -> dict:
    """Retrieve question-level survey results without merging unlike waves or samples."""
    adapters = registry.get_all()
    if not adapters:
        return {
            "status": "not_connected",
            "results": [],
            "sources_searched": [],
            "source_failures": [],
        }

    responses = await asyncio.gather(
        *(adapter.search(query) for adapter in adapters),
        return_exceptions=True,
    )
    results = []
    failures = []
    searched = []

    for adapter, response in zip(adapters, responses):
        searched.append(adapter.name)
        if isinstance(response, Exception):
            failures.append({"source": adapter.name, "error": str(response)})
            continue
        try:
            source_results = []
            for item in response[:query.limit]:
                # Validate every provider payload before it can reach the UI.
                validated = SurveyQuestionResult.model_validate(item)
                source_results.append(validated.model_dump(mode="json"))
            results.extend(source_results)
        except Exception as exc:
            failures.append({"source": adapter.name, "error": str(exc)})

    return {
        "status": "completed" if results else "no_results",
        "results": results,
        "sources_searched": searched,
        "source_failures": failures,
    }
