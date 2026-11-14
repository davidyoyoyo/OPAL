# OPAL survey data standard

OPAL must treat a measured opinion as a question-level survey result, not as a number found in an abstract.

A survey connector may emit a `SurveyQuestionResult` only when it can preserve:

- Exact original question wording and answer-option labels.
- Source archive, dataset identifier, title and a stable source URL.
- Population and geography.
- Total sample size and the base for this exact question (when reported).
- Fieldwork dates and survey wave (when reported).
- Weighting information and any relevant base/skip instructions.
- The original response counts and/or percentages, with the percentage provenance stated.

## Calculation rules

- If the source reports percentages, preserve them as source-reported.
- If OPAL calculates a percentage, use `count / base_n * 100`, never the total study sample by default.
- Do not calculate a percentage if the question-specific denominator is unknown.
- Keep "Don't know", "No opinion", neutral, mixed and undecided as distinct categories unless the source explicitly combines them.
- Preserve each survey wave, country, population and question wording separately.
- Never pool studies with different designs or denominators just to create one chart.
- Never expose respondent-level microdata in the public research response.

## Provider acceptance

Before connecting a survey archive, review its current terms for commercial use, redistribution of derived aggregates, attribution, registration/API requirements, rate limits and retention. A free download is not automatically a commercial reuse licence.

The current Crossref connector is for scholarly publication discovery, not survey response data. The current Eurostat connector discovers statistical datasets; it is not yet a question-level opinion survey connector. Until a compatible provider is implemented, the API must return an explicit `not_connected` status and an empty survey-results list.
