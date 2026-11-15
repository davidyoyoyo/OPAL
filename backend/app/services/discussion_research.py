import asyncio

from app.sources.discussion_base import DiscussionQuery, DiscussionRecord
from app.sources.discussion_registry import DiscussionSourceRegistry


async def run_discussion_search(query: DiscussionQuery, registry: DiscussionSourceRegistry) -> dict:
    """Retrieve public discussion samples while isolating provider failures."""
    adapters = registry.get_all()
    if not adapters:
        return {
            "status": "not_connected",
            "results": [],
            "sources_searched": [],
            "source_failures": [],
        }

    responses = await asyncio.gather(
        *(adapter.search(query) for adapter in adapters),
        return_exceptions=True,
    )
    results: list[DiscussionRecord] = []
    failures: list[dict[str, str]] = []
    searched: list[str] = []
    for adapter, response in zip(adapters, responses):
        searched.append(adapter.name)
        if isinstance(response, Exception):
            failures.append({"source": adapter.name, "error": str(response)})
            continue
        results.extend(response[:query.limit])

    # Deduplicate by provider record ID without merging unlike posts.
    unique: dict[str, DiscussionRecord] = {}
    for item in results:
        unique.setdefault(item.id, item)

    return {
        "status": "completed" if unique else ("partial_failure" if failures else "no_results"),
        "results": [item.model_dump(mode="json") for item in list(unique.values())[:query.limit]],
        "sources_searched": searched,
        "source_failures": failures,
    }
