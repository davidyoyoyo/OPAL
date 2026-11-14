from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.core.config import settings
from app.services.research import run_research
from app.sources.registry import source_registry


app = FastAPI(title=settings.app_name, version=settings.api_version)


class ResearchRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)


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
