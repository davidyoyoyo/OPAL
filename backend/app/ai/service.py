import os

from app.ai.base import StructuredAIProvider
from app.ai.prompts import (
    discussion_batch_prompt,
    evidence_prompt,
    evidence_synthesis_prompt,
    research_plan_prompt,
)
from app.ai.schemas import DiscussionBatchInterpretation, EvidenceInterpretation, ResearchPlan
from app.ai.synthesis import EvidenceSynthesis


class AIInterpretationService:
    def __init__(self, provider: StructuredAIProvider) -> None:
        self.provider = provider

    async def interpret_question(self, question: str) -> ResearchPlan:
        system, user = research_plan_prompt(question, ResearchPlan)
        return await self.provider.generate_structured(
            system_prompt=system, user_prompt=user, output_model=ResearchPlan
        )

    async def interpret_evidence(self, text: str, source_context: dict | None = None) -> EvidenceInterpretation:
        system, user = evidence_prompt(text, source_context or {}, EvidenceInterpretation)
        return await self.provider.generate_structured(
            system_prompt=system, user_prompt=user, output_model=EvidenceInterpretation
        )

    async def interpret_discussions(
        self, question: str, records: list[dict]
    ) -> DiscussionBatchInterpretation:
        bounded_records = records[:50]
        system, user = discussion_batch_prompt(question, bounded_records, DiscussionBatchInterpretation)
        return await self.provider.generate_structured(
            system_prompt=system,
            user_prompt=user,
            output_model=DiscussionBatchInterpretation,
        )

    async def synthesize_evidence(
        self, question: str, source_passages: list[dict]
    ) -> EvidenceSynthesis:
        system, user = evidence_synthesis_prompt(question, source_passages, EvidenceSynthesis)
        return await self.provider.generate_structured(
            system_prompt=system, user_prompt=user, output_model=EvidenceSynthesis
        )


def create_ai_service_from_env() -> AIInterpretationService | None:
    """Return None when AI is not configured; never silently pretend a rule-based result is AI."""
    provider_name = os.getenv("OPAL_AI_PROVIDER", "").strip().lower()
    if not provider_name:
        return None
    if provider_name != "cloudflare_workers_ai":
        raise ValueError(f"Unsupported OPAL_AI_PROVIDER: {provider_name}")

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    model = os.getenv("OPAL_AI_MODEL", "").strip()
    if not all((account_id, api_token, model)):
        raise ValueError(
            "Cloudflare AI requires CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, and OPAL_AI_MODEL."
        )

    from app.ai.providers.cloudflare_workers_ai import CloudflareWorkersAIProvider

    return AIInterpretationService(CloudflareWorkersAIProvider(account_id, api_token, model))
