import csv
import io
import re

import httpx

from app.sources.base import RawSourceItem, SourceAdapter, SourceQuery


class EurostatAdapter(SourceAdapter):
    """Discover public Eurostat datasets; numeric extraction is a separate step."""

    name = "eurostat"
    description = "Official European statistical datasets and survey indicators"

    catalogue_url = (
        "https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt"
    )
    browser_url = "https://ec.europa.eu/eurostat/databrowser/view/{code}/default/table?lang=en"

    _STOPWORDS = {
        "about", "after", "also", "and", "are", "can", "does", "for", "from",
        "how", "many", "much", "people", "percentage", "percent", "the", "what",
        "with", "like", "love", "prefer", "support",
    }

    @classmethod
    def _query_terms(cls, query: str) -> set[str]:
        return {
            term for term in re.findall(r"[a-z0-9]{3,}", query.lower())
            if term not in cls._STOPWORDS
        }

    async def search(self, request: SourceQuery) -> list[RawSourceItem]:
        terms = self._query_terms(request.query)
        if not terms:
            return []

        headers = {"User-Agent": "OPALResearch/0.2 (official statistics discovery)"}
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(self.catalogue_url, params={"lang": "en"})
            response.raise_for_status()

        # The official TXT catalogue is tab-separated and quoted. It contains
        # folders, predefined tables and downloadable datasets; keep the latter
        # two, and never interpret catalogue metadata as measured results.
        reader = csv.DictReader(io.StringIO(response.text), delimiter="\t")
        ranked: list[tuple[int, dict[str, str]]] = []
        for row in reader:
            title = (row.get("title") or "").strip()
            code = (row.get("code") or "").strip()
            item_type = (row.get("type") or "").strip().lower()
            if not title or not code or item_type not in {"dataset", "table"}:
                continue

            title_terms = set(re.findall(r"[a-z0-9]{3,}", title.lower()))
            hits = len(terms & title_terms)
            if hits:
                ranked.append((hits, row))

        ranked.sort(key=lambda pair: (pair[0], pair[1].get("title", "")), reverse=True)
        records: list[RawSourceItem] = []
        for _, row in ranked[: request.limit]:
            code = row["code"].strip()
            title = row["title"].strip()
            start = (row.get("data start") or "").strip()
            end = (row.get("data end") or "").strip()
            updated = (row.get("last update of data") or "").strip()
            value_count = (row.get("values") or "").strip()
            description_parts = [
                "Eurostat catalogue entry; this is dataset metadata, not a result.",
                f"Data coverage: {start or 'not stated'} to {end or 'not stated'}.",
                f"Last data update: {updated or 'not stated'}.",
            ]
            records.append(
                RawSourceItem(
                    provider=self.name,
                    provider_record_id=code,
                    url=self.browser_url.format(code=code),
                    title=title,
                    abstract=" ".join(description_parts),
                    identifiers={"eurostat_code": code},
                    raw_metadata={
                        "dataset_code": code,
                        "catalogue_type": (row.get("type") or "").strip(),
                        "data_start": start or None,
                        "data_end": end or None,
                        "last_update": updated or None,
                        "value_count": value_count or None,
                        "evidence_role": "supporting_statistics",
                    },
                )
            )
        return records
