# OPAL research engine

The backend is a separate Python service. From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the API explorer.

## Add a source connector

1. Create a class in `app/sources/providers/` that inherits `SourceAdapter`.
2. Implement `async def search(self, request: SourceQuery) -> list[RawSourceItem]`.
3. Map the provider's response into the provider-neutral `RawSourceItem` model.
4. Register the adapter in the application startup configuration.
5. Add tests using saved provider responses (not live API calls).

A connector should only retrieve and normalize source records. It should not decide whether two records are the same study, calculate opinion percentages, or write directly to the database.

## Duplicate-study model

A **study** is the underlying research work. A **source location** is one website/page that hosts or indexes it. One study can have many source locations.

- Matching normalized DOI: strong identity; source locations are grouped under one study.
- Similar title, authors and year: possible duplicate only; keep records separate until reviewed.
- No stable identifier: unresolved identity; never silently merge based on title alone.

This prevents the same paper mirrored across several websites from being counted as several independent studies. Distinct datasets or survey waves from the same research programme must still be represented as distinct study instances when their methods, samples or field dates differ.

## Current scope

The engine has three separate evidence families:

- **Scholarly sources:** Crossref provides publication metadata. Its search calls are serialized, cached for 30 minutes and retried with backoff after 429/5xx responses.
- **Official statistics:** Eurostat discovers statistical datasets. The current connector does not extract question-level opinion results.
- **Public discussions:** Bluesky searches a bounded set of public posts for the user's topic. This is expressed online opinion, not a representative survey.

No question-level survey adapter is registered yet. The measured-opinions section therefore remains empty rather than inventing percentages. Eurobarometer aggregate XLSX files are the leading candidate, but each dataset's licence and workbook structure must be validated before integration.

Adding a provider in one evidence family must not cause its records to be treated as records in another family. Survey measurements, discussion posts and scholarly studies have separate schemas and registries.

## Database setup

OPAL uses PostgreSQL in production and SQLAlchemy 2.x in the backend. The
initial SQL migration is at `migrations/0001_initial_schema.sql`.

1. Install PostgreSQL and create a database named `opal` (or use a database
   URL supplied by your hosting provider).
2. Set `DATABASE_URL` before starting the API. Example:

   ```bash
   export DATABASE_URL="postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@localhost:5432/opal"
   ```

3. Apply the initial schema using the PostgreSQL command-line client:

   ```bash
   psql "$DATABASE_URL" -f migrations/0001_initial_schema.sql
   ```

4. Install backend dependencies and run the API:

   ```bash
   pip install -e ".[dev]"
   uvicorn app.main:app --reload
   ```

The SQLAlchemy table definitions live in `app/db/models.py`. The request-scoped
session dependency is `app/db/session.py:get_db`. The engine is created lazily
with respect to connections: importing the application does not require a
running database. The current API routes do not yet write research results to
the database; persistence will be added in the next backend step.

For a lightweight model smoke test, the test suite creates the SQLAlchemy
metadata against in-memory SQLite. PostgreSQL-specific behavior (including
the production migration) still needs to be checked against a real PostgreSQL
instance before deployment.


## Connected providers and configuration

All provider calls are made by the backend; API keys must never be placed in frontend code.

### Eurostat

- Public REST and catalogue APIs; no API key or registration is required.
- Eurostat describes the APIs as free of charge. Its public documentation does not state a fixed numeric requests-per-second quota. It does apply fair-use controls to large/repeated extractions; some requests can be queued and processed asynchronously.
- Statistical data may generally be reused commercially with source attribution, subject to dataset-specific notices and listed exceptions. The connector currently discovers catalogue entries only.
- Eurostat updates datasets twice daily when new data or structural changes are available.
- No environment variable is required.

### Crossref

- No API key is required.
- Crossref applies stricter limits to list/search requests than single-record lookups. OPAL deliberately sends one serialized list request at a time, no faster than once per second, caches successful results for 30 minutes and backs off on 429/5xx responses.
- Almost all bibliographic metadata is reusable; abstracts may remain copyrighted by publishers/authors.
- Set `OPAL_CROSSREF_MAILTO` to a real monitored contact email to identify OPAL as a polite-pool client. OPAL remains conservative even when using that pool.

### Bluesky

- Public search is accessed without an API key through the documented public AppView endpoint.
- OPAL performs one bounded, user-initiated search per question and does not crawl or bulk-download the network.
- Public API availability and rate limits can change. A 403/429 is shown as a source failure rather than silently retried indefinitely.
- The adapter does not retain author display names or profile metadata. It preserves the original post URL.
- AI classifies relevance and stance; Python validates returned post IDs and calculates descriptive proportions within the retrieved sample. Those proportions are not representative of all people or all Bluesky users.

### AI processing

Set `OPAL_AI_PROVIDER=cloudflare_workers_ai`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, and `OPAL_AI_MODEL` in the backend process environment. AI creates the research plan and classifies bounded discussion batches. Python validates IDs and performs sample arithmetic. If AI is not configured, OPAL still retrieves posts but does not invent stance labels or percentages.

### Not enabled

- **European Social Survey (ESS):** free access is for non-commercial use; commercial use is generally not allowed except case-by-case. That does not meet OPAL's intended public/commercial compatibility requirement.
- **World Values Survey (WVS):** its download conditions limit use to non-profit purposes and prohibit redistribution of the data files.
- **Eurobarometer via GESIS:** microdata downloads are free after registration, but the available documentation does not by itself clearly grant OPAL the right to republish or commercially use the microdata. Keep it out of automated ingestion until GESIS confirms those rights in writing.

Do not treat an API being free to access as permission to republish its underlying survey data. For every survey provider, OPAL must record the exact dataset licence and distinguish permission to publish derived aggregate statistics from permission to redistribute raw microdata.
