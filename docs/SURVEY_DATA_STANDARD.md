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


## Initial repository review

- **Eurobarometer aggregate tables are a promising first candidate.** The European Data Portal lists downloadable XLSX volumes containing weighted frequencies by country and EU-level results. Its read-only API can discover datasets, but each dataset and distribution must still be checked for its actual licence and documentation before ingestion.
- **GESIS-hosted Eurobarometer microdata is not a default OPAL source.** GESIS access conditions vary by dataset/access class, and its current general terms prohibit commercial use unless a dataset expressly says otherwise. Some downloads also require registration. This does not meet OPAL's requirement for a blanket, no-cost commercial reuse path.
- **European Social Survey is not a default OPAL source either.** Its API is currently a beta file-download endpoint, and ESS ERIC materials describe non-commercial reuse as the general rule, with commercial use handled case by case.

A future Eurobarometer aggregate connector should first retrieve dataset metadata and distribution licences from the European Data Portal, reject records without a compatible explicit reuse licence, then parse the published XLSX volumes while retaining the question wording, answer labels, weighted/unweighted base, geography, wave, fieldwork dates and workbook URL. It must not treat a survey's overall sample size as the base for every question.
\n\n## Eurobarometer integration status\n\nThe European Data Portal currently lists Standard Eurobarometer 105 (Spring 2026) and other waves with processed XLSX distributions. Volume A is described as containing weighted frequencies for each country/territory and EU-level results. This makes the aggregate files a promising measured-opinion source. However, the portal explicitly notes that licences are dataset-specific and that it also harvests non-commercial datasets. OPAL must inspect the exact licence and distribution metadata for each dataset before ingesting it. The workbook parser must also prove that it can recover original question wording, response labels, weighted base and fieldwork metadata before any results are displayed. Until those checks are complete, this source remains a candidate, not a connected survey adapter.\n