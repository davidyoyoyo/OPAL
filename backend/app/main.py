from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.core.config import settings
from app.services.research import run_research
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/sources")
async def list_sources() -> dict:
    return {"sources": source_registry.public_catalog()}


@app.post("/research")
async def research(request: ResearchRequest) -> dict:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")
    return await run_research(question, source_registry)


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
