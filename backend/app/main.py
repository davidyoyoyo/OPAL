import asyncio
from collections import Counter

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.research import is_prevalence_question, run_research
from app.services.synthesis import build_extractive_synthesis
from app.services.survey_research import run_survey_search
from app.services.discussion_research import run_discussion_search
from app.sources.survey_base import SurveyQuery
from app.sources.survey_registry import survey_registry
from app.sources.discussion_base import DiscussionQuery
from app.sources.discussion_registry import discussion_registry
from app.sources.registry import source_registry
from app.sources.providers.crossref import CrossrefAdapter
from app.sources.providers.eurostat import EurostatAdapter
from app.sources.providers.bluesky import BlueskyAdapter
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

# Each evidence family has its own registry and validation rules.
source_registry.register(CrossrefAdapter())
source_registry.register(EurostatAdapter())
discussion_registry.register(BlueskyAdapter())


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


def _validated_synthesis(ai_synthesis, source_passages: list[dict]) -> dict:
    """Reject model-generated citations that do not point to supplied records."""
    valid_ids = {str(item.get("source_id", "")) for item in source_passages}
    output = ai_synthesis.model_dump()
    overview_ids = [
        source_id for source_id in output.get("overview_source_ids", [])
        if source_id in valid_ids
    ]
    if not overview_ids:
        raise AIInterpretationError("Synthesis overview did not cite a retrieved source.")
    safe_points = []
    for point in output.get("key_points", []):
        source_ids = [source_id for source_id in point.get("source_ids", []) if source_id in valid_ids]
        if source_ids:
            safe_points.append({**point, "source_ids": source_ids})
    if not safe_points:
        raise AIInterpretationError("Synthesis did not return any source-backed key points.")
    output["overview_source_ids"] = overview_ids
    output["key_points"] = safe_points
    output["mode"] = "ai_synthesis"
    return output


def _analyse_discussions(question: str, records: list[dict], batch) -> tuple[list[dict], dict]:
    """Validate AI labels and calculate descriptive sample statistics in Python."""
    valid_ids = {str(item.get("id", "")) for item in records}
    labels = {}
    for label in batch.interpretations:
        if label.id in valid_ids and label.id not in labels:
            labels[label.id] = label

    enriched = []
    for record in records:
        label = labels.get(str(record.get("id", "")))
        enriched.append({
            **record,
            "relevant": label.relevant if label else None,
            "stance": label.stance if label else "unclear",
            "analysis_summary": label.summary if label else "",
            "analysis_confidence": label.confidence if label else None,
        })

    relevant_labels = [
        label for label in labels.values()
        if label.relevant and label.confidence >= 0.55
    ]
    classifiable = [
        label for label in relevant_labels
        if label.stance != "unclear"
    ]
    counts = Counter(label.stance for label in classifiable)
    denominator = len(classifiable)
    distribution = [
        {
            "stance": stance,
            "count": count,
            "percentage": round(count / denominator * 100, 1) if denominator else None,
        }
        for stance, count in sorted(counts.items())
    ]
    return enriched, {
        "status": "completed",
        "sampled_posts": len(records),
        "relevant_posts": len(relevant_labels),
        "classified_posts": denominator,
        "stance_distribution": distribution,
        "note": (
            "Percentages describe only the retrieved, relevant and classifiable public posts in this "
            "Bluesky search sample. They are not a representative estimate of the general population. "
            "The sample is shaped by platform use, search ranking, language, time and who chooses to post."
        ),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/sources")
async def list_sources() -> dict:
    return {
        "scholarly_sources": source_registry.public_catalog(),
        "survey_sources": survey_registry.public_catalog(),
        "discussion_sources": discussion_registry.public_catalog(),
    }


@app.post("/research")
async def research(request: ResearchRequest) -> dict:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    # Interpret the question first. The concise topic guides provider retrieval,
    # while relevance checks and all evidence claims retain the original wording.
    ai_service = None
    plan = None
    ai_configuration_status = "not_configured"
    try:
        ai_service = create_ai_service_from_env()
        if ai_service is not None:
            ai_configuration_status = "configured"
            plan = await ai_service.interpret_question(question)
    except Exception:
        ai_configuration_status = "partial_failure"

    retrieval_topic = plan.topic if plan is not None else question
    research_result, survey_search, discussion_search = await asyncio.gather(
        run_research(question, source_registry, search_query=retrieval_topic),
        run_survey_search(SurveyQuery(question=question), survey_registry),
        run_discussion_search(
            DiscussionQuery(question=question, topic=retrieval_topic),
            discussion_registry,
        ),
    )
    result = research_result
    findings = result.get("findings", [])
    result["evidence_synthesis"] = build_extractive_synthesis(question, findings)

    result["survey_results"] = survey_search["results"]
    result["survey_source_failures"] = survey_search["source_failures"]
    result["survey_data_status"] = {
        "status": survey_search["status"],
        "sources_searched": survey_search["sources_searched"],
        "message": (
            "No question-level survey repository is currently connected. Crossref provides scholarly "
            "publication metadata and Eurostat currently discovers statistical datasets; neither "
            "connector supplies original public-opinion question distributions here. OPAL therefore "
            "shows no measured-opinion percentages for this search."
            if survey_search["status"] == "not_connected"
            else (
                "Connected survey sources were searched, but none returned a matching question-level "
                "distribution with its original wording and denominator."
                if survey_search["status"] == "no_results"
                else "Question-level survey results were retrieved from the connected survey sources."
            )
        ),
    }

    result["discussion_results"] = discussion_search["results"]
    result["discussion_sources_searched"] = discussion_search["sources_searched"]
    result["discussion_source_failures"] = discussion_search["source_failures"]
    result["discussion_analysis"] = {
        "status": "not_configured" if ai_service is None else "not_attempted",
        "sampled_posts": len(discussion_search["results"]),
        "relevant_posts": 0,
        "classified_posts": 0,
        "stance_distribution": [],
        "note": (
            "Public posts are expressions from a platform sample, not a population survey. "
            "Configure OPAL's AI provider to classify relevance and stance; no percentages are inferred."
        ),
    }

    if plan is not None:
        result["research_plan"] = plan.model_dump()

    result["ai_processing"] = {
        "status": ai_configuration_status,
        "question_interpretation": "completed" if plan is not None else "unavailable",
        "synthesis": "not_attempted",
        "discussion_analysis": "not_attempted",
    }

    if ai_service is None:
        result["ai_processing"]["discussion_analysis"] = "not_configured"
        return result

    discussion_records = discussion_search["results"]
    if discussion_records:
        try:
            batch = await ai_service.interpret_discussions(
                question,
                [{"id": item["id"], "text": item["text"][:600]} for item in discussion_records[:25]],
            )
            enriched, analysis = _analyse_discussions(question, discussion_records, batch)
            result["discussion_results"] = enriched
            result["discussion_analysis"] = analysis
            result["ai_processing"]["discussion_analysis"] = "completed"
        except Exception:
            result["discussion_analysis"]["status"] = "partial_failure"
            result["discussion_analysis"]["note"] += " AI classification failed for this request."
            result["ai_processing"]["discussion_analysis"] = "partial_failure"
    else:
        result["discussion_analysis"]["status"] = "no_results"
        result["ai_processing"]["discussion_analysis"] = "no_posts_to_classify"

    synthesis_findings = (
        [item for item in findings if item.get("evidence_role") == "explanatory_context"]
        if is_prevalence_question(question) else findings
    )
    if synthesis_findings:
        source_passages = [
            {
                "source_id": str(item.get("id") or item.get("source_url") or item.get("source_title") or ""),
                "source_title": item.get("source_title"),
                "source_url": item.get("source_url"),
                "publication_year": item.get("publication_year"),
                "passage": str(item.get("evidence_text") or item.get("summary") or "")[:2500],
                "evidence_level": item.get("evidence_level"),
                "evidence_role": item.get("evidence_role"),
            }
            for item in synthesis_findings[:20]
        ]
        try:
            synthesis = await ai_service.synthesize_evidence(question, source_passages)
            result["evidence_synthesis"] = _validated_synthesis(synthesis, source_passages)
            result["ai_processing"]["synthesis"] = "completed"
        except Exception:
            result["ai_processing"]["synthesis"] = "partial_failure"
    elif findings and is_prevalence_question(question):
        result["ai_processing"]["synthesis"] = "no_explanatory_studies"
    else:
        result["ai_processing"]["synthesis"] = "no_abstracts_to_synthesize"

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
