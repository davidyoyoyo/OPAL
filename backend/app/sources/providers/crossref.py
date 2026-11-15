import asyncio
import email.utils
import os
import time
from datetime import datetime, timezone

import httpx

from app.sources.base import RawSourceItem, SourceAdapter, SourceQuery


class CrossrefAdapter(SourceAdapter):
    """Search Crossref conservatively and recover from temporary rate limits."""

    name = "crossref"
    description = "Scholarly publication metadata indexed by Crossref"
    endpoint = "https://api.crossref.org/works"
    _select = "DOI,title,author,published,published-print,published-online,abstract,URL,type"

    def __init__(self, minimum_interval: float = 1.0, cache_ttl: float = 1800.0) -> None:
        # List queries have stricter limits than single-record lookups. One
        # serialized request per second is deliberately conservative for both
        # public and polite pools and avoids the old parallel-query burst.
        self.minimum_interval = max(1.0, minimum_interval)
        self.cache_ttl = cache_ttl
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0
        self._cache: dict[str, tuple[float, list[RawSourceItem]]] = {}

    @staticmethod
    def build_topic_query(query: str) -> str:
        ignored = {
            "how", "many", "much", "people", "person", "do", "does", "like",
            "likes", "love", "loves", "what", "percentage", "percent", "is",
            "are", "the", "a", "an", "of", "to", "about", "think", "opinion",
        }
        topic = " ".join(
            token.strip(".,!?;:\"'()[]{}")
            for token in query.lower().split()
            if token.strip(".,!?;:\"'()[]{}") not in ignored
        ).strip()
        return topic or query.strip()

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(60.0, max(0.0, float(retry_after)))
            except ValueError:
                try:
                    retry_date = email.utils.parsedate_to_datetime(retry_after)
                    if retry_date.tzinfo is None:
                        retry_date = retry_date.replace(tzinfo=timezone.utc)
                    return min(60.0, max(0.0, (retry_date - datetime.now(timezone.utc)).total_seconds()))
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(30.0, 1.0 * (2 ** attempt))

    async def _fetch_payload(self, client: httpx.AsyncClient, params: dict) -> dict:
        async with self._lock:
            for attempt in range(4):
                wait = self.minimum_interval - (time.monotonic() - self._last_request_at)
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last_request_at = time.monotonic()
                response = await client.get(self.endpoint, params=params)
                if response.status_code == 429 or response.status_code in {500, 502, 503, 504}:
                    if attempt == 3:
                        response.raise_for_status()
                    await asyncio.sleep(self._retry_delay(response, attempt))
                    continue
                response.raise_for_status()
                return response.json()
        raise RuntimeError("Crossref request did not return a response.")

    async def search(self, request: SourceQuery) -> list[RawSourceItem]:
        topic_query = self.build_topic_query(request.query)
        cache_key = f"{topic_query.casefold()}|{min(request.limit, 100)}"
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] < self.cache_ttl:
            return list(cached[1])

        headers = {"User-Agent": "OPALResearch/0.4 (scholarly metadata discovery)"}
        params = {
            "query.bibliographic": topic_query,
            "rows": min(request.limit, 100),
            "select": self._select,
        }
        mailto = os.getenv("OPAL_CROSSREF_MAILTO", "").strip()
        if mailto:
            params["mailto"] = mailto

        async with httpx.AsyncClient(timeout=25.0, headers=headers) as client:
            payload = await self._fetch_payload(client, params)

        records: list[RawSourceItem] = []
        seen_ids: set[str] = set()
        for item in payload.get("message", {}).get("items", []):
            record_id = (item.get("DOI") or item.get("URL") or "").lower()
            if record_id and record_id in seen_ids:
                continue
            if record_id:
                seen_ids.add(record_id)

            titles = item.get("title") or []
            title = titles[0].strip() if titles and titles[0] else ""
            if not title:
                continue

            date_parts = (
                item.get("published", {}).get("date-parts")
                or item.get("published-print", {}).get("date-parts")
                or item.get("published-online", {}).get("date-parts")
                or []
            )
            year = date_parts[0][0] if date_parts and date_parts[0] else None
            authors = [
                " ".join(part for part in [author.get("given"), author.get("family")] if part)
                for author in item.get("author", [])
            ]
            authors = [author for author in authors if author]

            records.append(
                RawSourceItem(
                    provider=self.name,
                    provider_record_id=item.get("DOI"),
                    url=item.get("URL") or f"https://doi.org/{item.get('DOI', '')}",
                    title=title,
                    abstract=item.get("abstract"),
                    doi=item.get("DOI"),
                    publication_year=year,
                    authors=authors,
                    raw_metadata={"type": item.get("type")},
                )
            )

        self._cache[cache_key] = (time.monotonic(), records)
        return list(records)
