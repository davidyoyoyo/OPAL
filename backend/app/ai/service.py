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


def _apply_prevalence_scope_defaults(question: str, plan: ResearchPlan) -> ResearchPlan:
    """Use transparent broad defaults instead of blocking prevalence research for missing scope."""
    if plan.intent != "prevalence":
        return plan

    updates = {}
    assumptions = list(plan.uncertainty_notes)

    if not plan.population:
        updates["population"] = "General population"

    if not plan.geography:
        updates["geography"] = "Worldwide"

    clarification = (plan.clarification_question or "").strip().lower()
    scope_terms = (
        "population", "geography", "country", "region", "location",
        "where", "which group", "who are you interested",
    )
    subject_ambiguity_terms = (
        "do you mean", "what do you mean", "refer to", "which jojo",
        "which person", "which character", "which series", "which title",
        "person or", "anime or", "character or", "series or",
    )

    asks_only_for_scope = (
        plan.clarification_needed
        and any(term in clarification for term in scope_terms)
        and not any(term in clarification for term in subject_ambiguity_terms)
    )

    if asks_only_for_scope:
        updates["clarification_needed"] = False
        updates["clarification_question"] = None

    if "population" in updates or "geography" in updates:
        assumption = (
            "Working scope defaults: general population and worldwide, because the question "
            "did not specify either. These defaults guide discovery and do not imply that "
            "worldwide representative evidence is available."
        )
        if assumption not in assumptions:
            assumptions.append(assumption)
        updates["uncertainty_notes"] = assumptions[:8]

    if updates:
        return plan.model_copy(update=updates)

    return plan


class AIInterpretationService:
    def __init__(self, provider: StructuredAIProvider) -> None:
        self.provider = provider

    async def interpret_question(self, question: str) -> ResearchPlan:
        system, user = research_plan_prompt(question, ResearchPlan)
        plan = await self.provider.generate_structured(
            system_prompt=system, user_prompt=user, output_model=ResearchPlan
        )
        return _apply_prevalence_scope_defaults(question, plan)

    async def interpret_evidence(self, text: str, source_context: dict | None = None) -> EvidenceInterpretation:
        system, user = evidence_prompt(text, source_context or {}, EvidenceInterpretation)
        return await self.provider.generate_structured(
            system_prompt=system, user_prompt=user, output_model=EvidenceInterpretation
        )

    async def interpret_discussions(
        self, question: str, records: list[dict]
    ) -> DiscussionBatchInterpretation:
        bounded_records = records[:25]
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
