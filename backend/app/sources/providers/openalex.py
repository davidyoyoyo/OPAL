import os

import httpx

from app.sources.base import RawSourceItem, SourceAdapter, SourceQuery


class OpenAlexAdapter(SourceAdapter):
    """Search OpenAlex's CC0 scholarly metadata API."""

    name = "openalex"
    description = "Open scholarly metadata from OpenAlex (CC0)"

    endpoint = "https://api.openalex.org/works"

    async def search(self, request: SourceQuery) -> list[RawSourceItem]:
        params: dict[str, str | int] = {
            "search": request.query,
            "per_page": min(request.limit, 100),
            "select": (
                "id,doi,title,publication_year,authorships,primary_location,"
                "open_access,type"
            ),
        }
        if request.date_from:
            params["filter"] = f"from_publication_date:{request.date_from}-01-01"
        if request.date_to:
            date_filter = f"to_publication_date:{request.date_to}-12-31"
            params["filter"] = f"{params['filter']},{date_filter}" if "filter" in params else date_filter

        api_key = os.getenv("OPAL_OPENALEX_API_KEY")
        if api_key:
            params["api_key"] = api_key

        headers = {"User-Agent": "OPALResearch/0.2 (scholarly discovery)"}
        async with httpx.AsyncClient(timeout=25.0, headers=headers) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
            payload = response.json()

        records: list[RawSourceItem] = []
        for item in payload.get("results", []):
            title = (item.get("title") or "").strip()
            if not title:
                continue

            doi = item.get("doi")
            if doi:
                doi = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")

            authors = []
            for authorship in item.get("authorships", []):
                author = authorship.get("author") or {}
                name = author.get("display_name")
                if name:
                    authors.append(name)

            location = item.get("primary_location") or {}
            landing_page = location.get("landing_page_url")
            source_url = landing_page or (f"https://doi.org/{doi}" if doi else item.get("id"))
            open_access = item.get("open_access") or {}

            records.append(
                RawSourceItem(
                    provider=self.name,
                    provider_record_id=item.get("id"),
                    url=source_url or item.get("id"),
                    title=title,
                    # Do not copy abstracts into OPAL from this discovery adapter.
                    # Keep metadata and the publisher/repository link; full-text
                    # and abstract reuse must be checked against the work's own licence.
                    abstract=None,
                    doi=doi,
                    publication_year=item.get("publication_year"),
                    authors=authors,
                    raw_metadata={
                        "openalex_id": item.get("id"),
                        "work_type": item.get("type"),
                        "is_oa": open_access.get("is_oa"),
                        "oa_status": open_access.get("oa_status"),
                        "oa_url": open_access.get("oa_url"),
                        "source_license": (
                            (location.get("license") or {}).get("id")
                            if isinstance(location.get("license"), dict)
                            else None
                        ),
                    },
                )
            )
        return records
