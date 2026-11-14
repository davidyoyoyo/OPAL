import httpx
from app.sources.base import RawSourceItem, SourceAdapter, SourceQuery


class CrossrefAdapter(SourceAdapter):
    """Search Crossref's public scholarly metadata API (no API key required)."""

    name = "crossref"
    description = "Scholarly publication metadata indexed by Crossref"

    endpoint = "https://api.crossref.org/works"

    async def search(self, request: SourceQuery) -> list[RawSourceItem]:
        params = {
            "query.bibliographic": request.query,
            "rows": request.limit,
            "select": "DOI,title,author,published,published-print,published-online,abstract,URL,type",
        }
        headers = {"User-Agent": "OPALResearch/0.1 (research discovery prototype)"}
        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
            payload = response.json()

        records: list[RawSourceItem] = []
        for item in payload.get("message", {}).get("items", []):
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
