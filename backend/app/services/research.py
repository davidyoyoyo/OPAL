import asyncio
from app.models.evidence import SourceLocation, StudyRecord
from app.sources.base import RawSourceItem, SourceQuery
from app.sources.registry import SourceRegistry
from app.deduplication.identity import compare_records, exact_identity_key


def group_source_records(items: list[RawSourceItem]) -> list[StudyRecord]:
    """Merge only records with the same strong identifier (currently DOI)."""
    studies: list[StudyRecord] = []
    doi_index: dict[str, int] = {}

    for item in items:
        key = exact_identity_key(item)
        if key and key in doi_index:
            existing = studies[doi_index[key]]
            existing.locations.append(
                SourceLocation(
                    provider=item.provider,
                    url=item.url,
                    provider_record_id=item.provider_record_id,
                )
            )
            continue

        study = StudyRecord(
            title=item.title,
            publication_year=item.publication_year,
            doi=item.doi,
            authors=item.authors,
            abstract=item.abstract,
            locations=[
                SourceLocation(
                    provider=item.provider,
                    url=item.url,
                    provider_record_id=item.provider_record_id,
                )
            ],
            identity_status="verified" if key else "unresolved",
        )
        if key:
            doi_index[key] = len(studies)
        studies.append(study)

    return studies


def find_duplicate_candidates(items: list[RawSourceItem]) -> list[dict]:
    """Return uncertain title/author matches for review; never merge them automatically."""
    candidates: list[dict] = []
    for left_index, left in enumerate(items):
        for right in items[left_index + 1:]:
            # Exact DOI duplicates are already grouped as the same study.
            score = compare_records(left, right)
            if score["reason"] == "possible_duplicate":
                candidates.append({
                    "left": {"provider": left.provider, "title": left.title, "url": left.url},
                    "right": {"provider": right.provider, "title": right.title, "url": right.url},
                    "confidence": score["confidence"],
                    "resolution": "needs_review",
                })
    return candidates


async def run_research(query: str, registry: SourceRegistry) -> dict:
    adapters = registry.get_all()
    if not adapters:
        return {
            "status": "no_sources_configured",
            "query": query,
            "message": "The engine is ready, but no source connectors are configured yet.",
            "studies": [],
            "duplicate_candidates": [],
            "sources_searched": [],
        }

    request = SourceQuery(query=query, limit=10)
    results = await asyncio.gather(
        *(adapter.search(request) for adapter in adapters),
        return_exceptions=True,
    )

    records: list[RawSourceItem] = []
    failures: list[dict[str, str]] = []
    for adapter, result in zip(adapters, results):
        if isinstance(result, Exception):
            failures.append({"source": adapter.name, "error": str(result)})
            continue
        records.extend(result)

    studies = group_source_records(records)
    duplicate_candidates = find_duplicate_candidates(records)
    return {
        "status": "completed" if records else "no_results",
        "query": query,
        "studies": [study.model_dump(mode="json") for study in studies],
        "duplicate_candidates": duplicate_candidates,
        "sources_searched": [adapter.name for adapter in adapters],
        "source_failures": failures,
        "raw_records_found": len(records),
        "unique_studies": len(studies),
    }
