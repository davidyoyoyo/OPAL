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

This is the first engine foundation: API routes, a connector contract, a registry, provider-neutral records and conservative DOI-based deduplication. It does not yet connect to external research websites or produce real findings. No placeholder result is returned as research.
