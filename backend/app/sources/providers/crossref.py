import asyncio

import httpx
from app.sources.base import RawSourceItem, SourceAdapter, SourceQuery


class CrossrefAdapter(SourceAdapter):
    """Search Crossref's public scholarly metadata API (no API key required)."""

    name = "crossref"
    description = "Scholarly publication metadata indexed by Crossref"

    endpoint = "https://api.crossref.org/works"

    async def search(self, request: SourceQuery) -> list[RawSourceItem]:
        # Crossref deprecated query.title. Search bibliographic metadata and
        # general indexed metadata separately, then merge the records.
        topic_query = " ".join(
            token for token in request.query.lower().replace("?", "").split()
            if token not in {
                "how", "many", "much", "people", "person", "do", "does",
                "like", "likes", "love", "loves", "what", "percentage",
                "percent", "is", "are", "the", "a", "an", "of", "to",
            }
        ) or request.query
        headers = {"User-Agent": "OPALResearch/0.2 (research discovery prototype)"}
        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            responses = await asyncio.gather(
                client.get(self.endpoint, params={
                    "query.bibliographic": topic_query,
                    "rows": request.limit,
                    "select": "DOI,title,author,published,published-print,published-online,abstract,URL,type",
                }),
                client.get(self.endpoint, params={
                    "query": f"{topic_query} preferences attitudes public opinion survey",
                    "rows": request.limit,
                    "select": "DOI,title,author,published,published-print,published-online,abstract,URL,type",
                }),
            )
            payloads = []
            for response in responses:
                response.raise_for_status()
                payloads.append(response.json())

        records: list[RawSourceItem] = []
        seen_ids: set[str] = set()
        merged_items = [
            item
            for payload in payloads
            for item in payload.get("message", {}).get("items", [])
        ]
        for item in merged_items:
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
        return records
