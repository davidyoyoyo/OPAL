import asyncio
import html
import re

from app.models.evidence import SourceLocation, StudyRecord
from app.sources.base import RawSourceItem, SourceQuery
from app.sources.registry import SourceRegistry
from app.deduplication.identity import compare_records, exact_identity_key


_STOPWORDS = {
    "about", "above", "after", "again", "against", "also", "among", "and", "are",
    "because", "been", "before", "being", "between", "both", "but", "can", "could",
    "does", "doing", "during", "each", "from", "have", "having", "into", "its",
    "more", "most", "not", "over", "same", "should", "some", "such", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "under", "until", "very", "was", "were", "what", "when",
    "where", "which", "while", "who", "will", "with", "would", "your",
    "care", "cum", "ce", "cea", "cei", "cele", "din", "despre", "este",
    "sunt", "pentru", "prin", "mai", "mult", "sau", "dar", "consider", "think",
    "people", "opinion", "opinions", "view", "views",
}


def _terms(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{3,}", text.lower())
        if token not in _STOPWORDS
    }


def relevance_score(query: str, item: RawSourceItem) -> float:
    """A transparent lexical relevance estimate; it is not a semantic judgement."""
    query_terms = _terms(query)
    if not query_terms:
        return 1.0
    title_terms = _terms(item.title)
    abstract_terms = _terms(item.abstract or "")
    title_coverage = len(query_terms & title_terms) / len(query_terms)
    abstract_coverage = len(query_terms & abstract_terms) / len(query_terms)
    return (0.75 * title_coverage) + (0.25 * abstract_coverage)


def is_relevant(query: str, item: RawSourceItem) -> bool:
    query_terms = _terms(query)
    if not query_terms:
        return True
    title_hits = len(query_terms & _terms(item.title))
    abstract_hits = len(query_terms & _terms(item.abstract or ""))
    score = relevance_score(query, item)
    return score >= 0.16 and (title_hits >= 1 or abstract_hits >= 2)


def _plain_abstract(value: str) -> str:
    """Remove JATS/HTML markup while retaining readable text and section labels."""
    value = re.sub(r"</(?:jats:)?(?:title|label)>", " — ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def extract_abstract_findings(query: str, studies: list[StudyRecord]) -> list[dict]:
    """
    Extract traceable abstract passages, not inferred survey outcomes.
    Each displayed passage is copied from the source abstract after markup cleanup.
    """
    query_terms = _terms(query)
    findings: list[dict] = []

    for study in studies:
        if not study.abstract:
            continue
        abstract = _plain_abstract(study.abstract)
        if len(abstract) < 45:
            continue

        sentences = [
            part.strip(" \t\n.;")
            for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", abstract)
            if len(part.strip()) >= 35
        ]
        if not sentences:
            sentences = [abstract]

        # Prefer explicitly labelled Results/Conclusion passages when Crossref
        # preserves structured abstract headings.
        labelled = [
            sentence for sentence in sentences
            if re.search(r"\b(results?|findings?|conclusions?)\s*[—:-]", sentence, re.I)
        ]
        candidates = labelled or sentences
        if query_terms:
            matching = [
                sentence for sentence in candidates
                if len(query_terms & _terms(sentence)) > 0
            ]
            candidates = matching or candidates

        excerpt = " ".join(candidates[:3]).strip()
        if len(excerpt) > 900:
            excerpt = excerpt[:897].rsplit(" ", 1)[0] + "..."

        source_url = str(study.locations[0].url) if study.locations else (
            f"https://doi.org/{study.doi}" if study.doi else ""
        )
        findings.append({
            "id": study.doi or source_url or study.title,
            "title": "Abstract evidence",
            "evidence_text": excerpt,
            "source_title": study.title,
            "source_url": source_url,
            "publication_year": study.publication_year,
            "evidence_type": "supporting_research",
            "evidence_level": "abstract",
            "interpretation": "Source passage, not an independently verified survey result or population estimate.",
        })

    return findings


def group_source_records(items: list[RawSourceItem]) -> list[StudyRecord]:
    """Merge only records with the same strong identifier (currently DOI)."""
    studies: list[StudyRecord] = []
    doi_index: dict[str, int] = {}
    for item in items:
        key = exact_identity_key(item)
        if key and key in doi_index:
            existing = studies[doi_index[key]]
            existing.locations.append(SourceLocation(
                provider=item.provider,
                url=item.url,
                provider_record_id=item.provider_record_id,
            ))
            if not existing.abstract and item.abstract:
                existing.abstract = item.abstract
            continue

        study = StudyRecord(
            title=item.title,
            publication_year=item.publication_year,
            doi=item.doi,
            identifiers=item.identifiers,
            authors=item.authors,
            abstract=item.abstract,
            locations=[SourceLocation(
                provider=item.provider,
                url=item.url,
                provider_record_id=item.provider_record_id,
            )],
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
            "findings": [],
            "duplicate_candidates": [],
            "sources_searched": [],
        }

    request = SourceQuery(query=query, limit=100)
    results = await asyncio.gather(
        *(adapter.search(request) for adapter in adapters),
        return_exceptions=True,
    )

    candidate_records: list[RawSourceItem] = []
    failures: list[dict[str, str]] = []
    for adapter, result in zip(adapters, results):
        if isinstance(result, Exception):
            failures.append({"source": adapter.name, "error": str(result)})
            continue
        candidate_records.extend(result)

    relevant_records = [item for item in candidate_records if is_relevant(query, item)]
    studies = group_source_records(relevant_records)
    findings = extract_abstract_findings(query, studies)
    duplicate_candidates = find_duplicate_candidates(relevant_records)

    return {
        "status": "completed" if relevant_records else "no_results",
        "query": query,
        "studies": [study.model_dump(mode="json") for study in studies],
        "findings": findings,
        "duplicate_candidates": duplicate_candidates,
        "sources_searched": [adapter.name for adapter in adapters],
        "source_failures": failures,
        "candidate_records_screened": len(candidate_records),
        "relevant_source_records": len(relevant_records),
        "raw_records_found": len(candidate_records),
        "unique_studies": len(studies),
        "abstracts_with_evidence": len(findings),
    }
