from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.research import run_research
from app.services.synthesis import build_extractive_synthesis
from app.services.survey_research import run_survey_search
from app.sources.survey_base import SurveyQuery
from app.sources.survey_registry import survey_registry
from app.sources.registry import source_registry
from app.sources.providers.crossref import CrossrefAdapter
from app.sources.providers.eurostat import EurostatAdapter
from app.ai.schemas import AIInterpretationError
from app.ai.service import create_ai_service_from_env


app = FastAPI(title=settings.app_name, version=settings.api_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Providers are registered here; the orchestration pipeline does not depend on
# any provider-specific implementation.
source_registry.register(CrossrefAdapter())
source_registry.register(EurostatAdapter())


class ResearchRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)


class EvidenceInterpretationRequest(BaseModel):
    text: str = Field(min_length=20, max_length=8000)
    source_context: dict = Field(default_factory=dict)


def _configured_ai_service():
    try:
        service = create_ai_service_from_env()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="AI processing is not configured correctly.") from exc
    if service is None:
        raise HTTPException(status_code=503, detail="AI processing is not enabled.")
    return service


def _validated_synthesis(ai_synthesis, findings: list[dict]) -> dict:
    """Reject model-generated citations that do not point to retrieved records."""
    valid_ids = {
        str(item.get("id") or item.get("source_url") or item.get("source_title") or "")
        for item in findings
    }
    output = ai_synthesis.model_dump()
    safe_points = []
    for point in output.get("key_points", []):
        source_ids = [source_id for source_id in point.get("source_ids", []) if source_id in valid_ids]
        if source_ids:
            safe_points.append({**point, "source_ids": source_ids})
    output["key_points"] = safe_points
    output["mode"] = "ai_synthesis"
    return output


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/sources")
async def list_sources() -> dict:
    return {
        "scholarly_sources": source_registry.public_catalog(),
        "survey_sources": survey_registry.public_catalog(),
    }


@app.post("/research")
async def research(request: ResearchRequest) -> dict:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    # The original question remains the retrieval query. AI may interpret and
    # synthesize retrieved evidence, but cannot silently redirect source search.
    result = await run_research(question, source_registry)
    findings = result.get("findings", [])

    # Always return a useful, clearly labelled fallback brief. When configured,
    # one structured AI call replaces it with a true cross-study synthesis.
    result["evidence_synthesis"] = build_extractive_synthesis(question, findings)
    survey_search = await run_survey_search(
        SurveyQuery(question=question),
        survey_registry,
    )
    result["survey_results"] = survey_search["results"]
    result["survey_source_failures"] = survey_search["source_failures"]
    result["survey_data_status"] = {
        "status": survey_search["status"],
        "sources_searched": survey_search["sources_searched"],
        "message": (
            "No survey repository is currently connected to OPAL. Crossref provides scholarly "
            "publication metadata and the current Eurostat connector discovers statistical datasets; "
            "neither supplies question-level opinion response distributions here. OPAL therefore "
            "shows no survey counts or percentages for this search."
            if survey_search["status"] == "not_connected"
            else (
                "Connected survey sources were searched, but none returned a matching question-level "
                "distribution with its original wording and denominator."
                if survey_search["status"] == "no_results"
                else "Question-level survey results were retrieved from the connected survey sources."
            )
        ),
    }
    result["ai_processing"] = {"status": "not_configured"}

    try:
        ai_service = create_ai_service_from_env()
    except ValueError:
        result["ai_processing"] = {"status": "configuration_error"}
        return result

    if ai_service is None:
        return result

    try:
        plan = await ai_service.interpret_question(question)
        result["research_plan"] = plan.model_dump()
        result["ai_processing"] = {"status": "question_interpreted", "synthesis": "not_attempted"}

        if findings:
            source_passages = [
                {
                    "source_id": str(item.get("id") or item.get("source_url") or item.get("source_title") or ""),
                    "source_title": item.get("source_title"),
                    "source_url": item.get("source_url"),
                    "publication_year": item.get("publication_year"),
                    "passage": str(item.get("evidence_text") or item.get("summary") or "")[:2500],
                    "evidence_level": item.get("evidence_level"),
                }
                for item in findings[:20]
            ]
            synthesis = await ai_service.synthesize_evidence(question, source_passages)
            result["evidence_synthesis"] = _validated_synthesis(synthesis, findings)
            result["ai_processing"]["synthesis"] = "completed"
        else:
            result["ai_processing"]["synthesis"] = "no_abstracts_to_synthesize"
    except AIInterpretationError:
        # Retrieved records and the deterministic fallback remain available if
        # the optional AI provider fails or returns invalid structured output.
        result["ai_processing"]["status"] = "partial_failure"

    return result


@app.post("/ai/interpret-question")
async def interpret_question(request: ResearchRequest) -> dict:
    service = _configured_ai_service()
    try:
        result = await service.interpret_question(request.question.strip())
        return result.model_dump()
    except AIInterpretationError as exc:
        raise HTTPException(status_code=502, detail="The AI provider could not interpret the question.") from exc


@app.post("/ai/interpret-evidence")
async def interpret_evidence(request: EvidenceInterpretationRequest) -> dict:
    service = _configured_ai_service()
    try:
        result = await service.interpret_evidence(request.text, request.source_context)
        return result.model_dump()
    except AIInterpretationError as exc:
        raise HTTPException(status_code=502, detail="The AI provider could not interpret the evidence.") from exc
