# OPAL engine architecture

## Guiding rule

Providers are replaceable inputs, not the architecture. Every connector converts one provider's API or permitted public data into OPAL's shared schema. The rest of the engine works against that schema.

```text
Question
  -> query interpretation
  -> source planner
  -> connector registry
       -> provider A adapter
       -> provider B adapter
       -> provider C adapter
  -> normalized source records
  -> study identity resolution / duplicate review
  -> evidence extraction
  -> quality and methodology checks
  -> typed evidence store
  -> statistics (code, not an LLM)
  -> report and export
```

## Connector boundary

Scholarly adapters implement `SourceAdapter.search(SourceQuery)` and return `RawSourceItem` objects. Survey adapters implement `SurveySourceAdapter` and return validated `SurveyQuestionResult` objects. Discussion adapters implement `DiscussionSourceAdapter` and return `DiscussionRecord` objects. These separate contracts prevent comments from being mistaken for studies or surveys. A provider-specific API change should be isolated to its adapter. Credentials are configured per provider through environment variables; never commit API keys.

## Three distinct entities

1. **Study** — the underlying paper, survey, report or dataset.
2. **Source location** — a URL/provider record where the study can be found. Many locations may point to one study.
3. **Evidence item** — a particular finding, statistic or argument extracted from a study or public discussion.

This separation is central to correct deduplication and provenance.

## Duplicate resolution

Use identifiers first (DOI, PMID, arXiv ID, provider-native stable IDs where their scope is known). Normalize DOI prefixes and casing. If no identifier exists, calculate candidate similarity from normalized title, author overlap, year and (later) abstract similarity. Candidate similarity must not silently merge records. Ambiguous pairs go to a review queue.

A repeated study is not a repeated independent observation. If two providers mirror the same paper, OPAL stores two source locations but one study. However, one paper can report multiple independent surveys or waves; those are separate study instances when their populations, samples, field dates or methods differ.

## Extensibility checklist for every new provider

- API terms, rate limits, robots/access policy and licensing checked.
- API key/auth handled via environment variables if required.
- Search pagination and retry/backoff implemented.
- Provider metadata mapped into the shared schema.
- Stable identifiers preserved.
- Source URL and retrieval timestamp retained.
- Saved-response tests added.
- Connector registered without changing downstream analysis code.

## Planned modules

- `sources/providers/`: one adapter per scholarly or discussion provider.\n- `sources/survey_providers/`: one adapter per survey archive.
- `deduplication/`: exact identifiers and candidate matching.
- `extraction/`: structured extraction of survey results and opinion themes.
- `quality/`: sample, date, geography, method, duplicate and representativeness checks.
- `storage/`: PostgreSQL repositories and migrations.
- `statistics/`: reproducible calculations using Python libraries.
- `services/`: orchestration of the pipeline.
