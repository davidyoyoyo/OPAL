# OPAL database model

Status: initial relational schema finalized for implementation.

## Decisions locked

1. **Aggregated respondent data only.** OPAL stores published aggregate counts and percentages. It does not store respondent-level rows, names, contact details, or respondent identifiers.
2. **Replace updated study versions.** A study has one current canonical record. When a verified correction or new release updates the same study/wave, OPAL updates that record in place; it does not retain parallel study-version copies. Distinct survey waves remain distinct because they are distinct observations.
3. **Bilingual text.** Preserve source-language wording and store an English translation separately. Never overwrite original wording with a translation. The language of each text field is explicit because one work may contain multilingual questions or findings.

## Entity map

```text
source_providers 1---* source_records *---1 research_works
                                      |
research_works 1---* surveys 1---* survey_waves
                                      |
                              survey_questions
                                      |
                               answer_options
                                      |
                           response_distributions

research_works 1---* qualitative_findings *---* argument_themes
                                      |
                               stance_categories

extraction_runs 1---* data_provenance *---1 source_records
```

## Tables and responsibilities

- **source_providers**: connector/provider catalogue (Crossref, a polling institute API, etc.). This is separate from individual records returned by a provider.
- **research_works**: canonical paper, report, survey publication, or dataset. Multiple provider records can resolve to one work.
- **source_records**: each provider's record/page for a work. Preserve provider-native IDs, URL, retrieval time, and raw metadata. A mirrored paper is not a second study.
- **surveys**: survey programme/instrument described by a work.
- **survey_waves**: a specific execution of a survey, with its own population, geography, fieldwork dates, sample and methodology. Different waves are never collapsed into one sample.
- **survey_questions**: exact question wording, question type, and language for a wave.
- **answer_options**: original answer-option wording plus a normalized stance category where applicable.
- **response_distributions**: aggregate counts and reported/calculated percentages for an answer option. The base is question-specific; do not assume the study's overall sample size is the denominator for every question.
- **stance_categories**: controlled categories: support, oppose, neutral, mixed, undecided, don't know, no opinion, other, unclassified. Neutral is not the same as don't know.
- **qualitative_findings**: extracted findings, themes, or short evidence excerpts from surveys, public discussions, or supporting research. Online discussion findings must retain their platform/time/population context and must not be presented as population estimates.
- **argument_themes** and **finding_argument_themes**: reusable themes and the many-to-many mapping between findings and themes.
- **extraction_runs**: append-only operational log of extraction jobs and software/model versions. This is not a historical copy of study content.
- **data_provenance**: traceability from an extracted record to its source record and precise location (page, table, question, section, or URL fragment), extraction method, confidence and verification status.

## Update and identity rules

- Resolve a work using strong identifiers first (DOI, PMID, arXiv ID, provider-native stable IDs). Similar titles alone create duplicate candidates; they do not justify automatic merging.
- A source record is unique by provider plus provider record ID when available. Refreshing it updates its current metadata and retrieval timestamp.
- A corrected release for the same study/wave replaces the stored current values in place. Keep extraction-run audit metadata, not a second full version of the study.
- A genuinely new wave, with a distinct field period/sample/population, gets a new `survey_waves` row.
- If a provider record is later found to represent a different work, correct the identity link through the deduplication/review workflow; do not silently merge.
- Provenance is attached to the specific extracted item, not merely to the publication as a whole. The application validates the polymorphic target in `data_provenance`.

## Statistical integrity rules

- Store response counts as integers where published. Store a reported percentage separately from a percentage calculated by OPAL; do not silently replace one with the other.
- Record `base_n` on each distribution row because denominators can differ between questions and, occasionally, between options.
- Keep missing/refused responses and multi-select question status explicit where the source reports them.
- Never calculate a percentage without a known denominator. If the source publishes only a percentage, counts may remain null.
- Keep raw answer wording and normalized category separate. Mapping to support/oppose is proposition-relative and may be unavailable for some questions.
- Do not combine survey distributions with counts of online comments into one denominator or imply that comments are a representative sample.
- Do not store respondent-level microdata in this initial schema.

## Language rules

For each supported text field, store:
- original text;
- BCP-47 language code for that original text;
- English translation in a separate nullable column.

An English original may have the same English text and no separate translation. A missing translation stays null; do not fabricate one. Translation provenance can be recorded in `data_provenance` / extraction metadata.

## Implementation notes

- PostgreSQL is the source of truth; UUID primary keys are used.
- JSONB is limited to provider-native metadata and flexible method details, not core relationships.
- The SQL migration in `backend/migrations/0001_initial_schema.sql` defines the initial tables, checks, indexes and foreign keys.
- No respondent table and no study-version table are intentionally present.
- The first implementation should use aggregated public/published data and respect each source's terms, licensing, and access restrictions.
