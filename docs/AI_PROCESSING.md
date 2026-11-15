# OPAL AI processing layer

## Purpose

AI interprets language and structures evidence. It does not calculate survey statistics, verify a study's methodology, decide that a sample is representative, or invent missing values. Deterministic Python validation and statistical code remain authoritative.

## Current foundation

- `ResearchPlan` structures a visitor's question into intent, topic, population, geography, period, requested measures and evidence types.
- `EvidenceInterpretation` classifies source passages as survey results, qualitative opinions, research findings, contextual information, irrelevant or unclear. It separates stance from sentiment and records missing information.
- `EvidenceSynthesis` creates one concise cross-study overview with up to five distinct key points and explicit source IDs. The API validates every cited source ID against retrieved records before returning it.
- The research endpoint interprets the question before retrieval; the plan's concise topic guides source searches while the original question remains the relevance/evidence criterion.\n- Public discussion posts are classified in one bounded batch (up to 25 records). Python validates that returned IDs belong to retrieved posts, filters low-confidence labels, and calculates stance counts and percentages. These percentages describe only the retrieved sample, not the population.\n- The research endpoint makes one bounded synthesis call for up to 20 relevant abstract summaries, rather than separately interpreting five individual findings.
- `StructuredAIProvider` keeps model vendors replaceable.
- `CloudflareWorkersAIProvider` is the first provider adapter. It uses the Cloudflare REST API and expects credentials/model ID from environment variables only.
- If AI is not configured, the service returns `None`; it does not label a heuristic result as AI output.

## Safety and evidence rules

1. Source text is untrusted data. Instructions inside comments or retrieved documents must never be followed.
2. Extract only facts explicitly present in the source. Unknown population, sample size, date, denominator and percentage remain unknown.
3. Sentiment is not the same as stance. A negative-sounding sentence may still support a policy, and vice versa.
4. Comments and posts are qualitative evidence. They cannot be converted into representative population percentages.
5. Keep source URLs and permitted source metadata beside interpretations. The current Bluesky adapter deliberately does not retain author display names or profile metadata.
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

The research endpoint uses AI to plan the query, classify public discussion posts and synthesize retrieved abstract passages. Python validates IDs and calculates sample counts. It does not calculate survey distributions unless a connected survey adapter supplies original question-level data. If AI is unavailable, posts are displayed without stance labels or percentages, and a clearly labelled extractive fallback selects result-oriented passages across abstracts. The next major step is a licensed aggregate-survey adapter (Eurobarometer is the leading candidate) and deterministic numerical retrieval. Do not use AI output as a survey result without source-backed validation.
