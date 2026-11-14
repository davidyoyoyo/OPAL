# OPAL AI processing layer

## Purpose

AI interprets language and structures evidence. It does not calculate survey statistics, verify a study's methodology, decide that a sample is representative, or invent missing values. Deterministic Python validation and statistical code remain authoritative.

## Current foundation

- `ResearchPlan` structures a visitor's question into intent, topic, population, geography, period, requested measures and evidence types.
- `EvidenceInterpretation` classifies source passages as survey results, qualitative opinions, research findings, contextual information, irrelevant or unclear. It separates stance from sentiment and records missing information.
- `StructuredAIProvider` keeps model vendors replaceable.
- `CloudflareWorkersAIProvider` is the first provider adapter. It uses the Cloudflare REST API and expects credentials/model ID from environment variables only.
- If AI is not configured, the service returns `None`; it does not label a heuristic result as AI output.

## Safety and evidence rules

1. Source text is untrusted data. Instructions inside comments or retrieved documents must never be followed.
2. Extract only facts explicitly present in the source. Unknown population, sample size, date, denominator and percentage remain unknown.
3. Sentiment is not the same as stance. A negative-sounding sentence may still support a policy, and vice versa.
4. Comments and posts are qualitative evidence. They cannot be converted into representative population percentages.
5. Keep source URL, author/source metadata where permitted, retrieval time and the exact evidence span beside every interpretation.
6. Validate all model output against Pydantic schemas. Invalid output is rejected, not repaired into invented facts.
7. Python performs deduplication, quality checks and all numerical calculations.

## Configuration

Set these only in the backend environment or deployment secret manager; never in frontend variables or Git:

- `OPAL_AI_PROVIDER=cloudflare_workers_ai`
- `CLOUDFLARE_ACCOUNT_ID=...`
- `CLOUDFLARE_API_TOKEN=...`
- `OPAL_AI_MODEL=...`

No credentials or model choice are committed. AI is inactive until configured. Cloudflare Workers AI has a daily free Neurons allowance; usage is model-dependent and exceeding the free allowance causes requests to fail on the Free plan. Review the current model catalogue and pricing before enabling it.

## Integration sequence

This module is the first AI-processing foundation. The next step is to connect question interpretation to the research planner and evidence interpretation to provider-specific extraction, with saved-response tests and explicit provenance. Do not use AI output as a survey result without source-backed validation.
