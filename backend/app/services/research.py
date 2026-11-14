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
    "how", "many", "much", "percentage", "percent", "common", "often",
    "like", "likes", "love", "loves", "prefer", "prefers", "people", "person",
    "sunt", "pentru", "prin", "mai", "mult", "sau", "dar", "consider", "think",
    "opinion", "opinions", "view", "views",
}


def _terms(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{3,}", text.lower())
        if token not in _STOPWORDS
    }


_CHOICE_WORDS = {"choose", "choosing", "choice", "choices", "select", "selecting", "selection", "selections"}
_OPINION_WORDS = {"like", "likes", "love", "prefer", "prefers", "preference", "preferences", "support", "favor", "favour", "attitude", "attitudes", "opinion", "opinions", "feel", "feeling"}
_SURVEY_SIGNALS = {"survey", "poll", "respondent", "respondents", "participant", "participants", "preference", "preferences", "attitude", "attitudes", "consumer", "consumers", "support", "favor", "favour"}
_EDUCATION_TERMS = {"ivy", "league", "university", "universities", "college", "colleges", "student", "students", "education", "admission", "admissions", "campus", "institution", "institutions", "higher"}
_DECISION_TERMS = {"choice", "decision", "factor", "factors", "important", "importance", "criteria", "select", "selection"}


def _normalized_terms(text: str) -> set[str]:
    terms = _terms(text)
    normalized = set(terms)
    if terms & _CHOICE_WORDS:
        normalized.add("choice")
    if terms & {"matters", "matter", "important", "importance"}:
        normalized.add("importance")
    return normalized


def relevance_score(query: str, item: RawSourceItem) -> float:
    """A conservative lexical score; shared generic wording is not enough."""
    query_terms = _normalized_terms(query)
    if not query_terms:
        return 1.0
    title_terms = _normalized_terms(item.title)
    abstract_terms = _normalized_terms(item.abstract or "")
    title_coverage = len(query_terms & title_terms) / len(query_terms)
    abstract_coverage = len(query_terms & abstract_terms) / len(query_terms)
    return (0.8 * title_coverage) + (0.2 * abstract_coverage)


def is_relevant(query: str, item: RawSourceItem) -> bool:
    """Reject lexical false positives by requiring the actual subject to match."""
    query_terms = _normalized_terms(query)
    if not query_terms:
        return False

    title_terms = _normalized_terms(item.title)
    abstract_terms = _normalized_terms(item.abstract or "")
    all_terms = title_terms | abstract_terms
    title_hits = len(query_terms & title_terms)
    abstract_hits = len(query_terms & abstract_terms)
    score = relevance_score(query, item)

    prevalence_question = bool(
        re.search(
            r"\\b(how many|what percentage|what percent|how common|do people|"
            r"people .*\\b(like|prefer|support|favor|favour)\\b|"
            r"(like|prefer|support|favor|favour))\\b",
            query,
            re.I,
        )
    )
    if prevalence_question:
        # The subject is the key noun/topic, not generic question wording.
        topic_terms = query_terms - _OPINION_WORDS - {
            "people", "person", "how", "many", "much", "common",
            "percentage", "percent",
        }
        if not topic_terms:
            return False

        matched_topics = topic_terms & all_terms
        survey_signal_count = len(_SURVEY_SIGNALS & all_terms)

        # A single-topic question (e.g. "How many people like pizza?")
        # must match that exact subject in the title, not just generic abstract
        # wording such as "what matters most" or "many students".
        if len(topic_terms) == 1:
            subject = next(iter(topic_terms))
            subject_in_title = subject in title_terms
            return subject_in_title and survey_signal_count >= 1

        # For multiword topics, require most of the topic to match and a
        # publication signal that it actually studies people's views/choices.
        required_topic_hits = 2 if len(topic_terms) >= 3 else 1
        return (
            len(matched_topics) >= required_topic_hits
            and survey_signal_count >= 1
            and score >= 0.16
        )

    # University-choice questions need both an education-domain match and a
    # decision/selection match. Generic shared wording is not enough.
    education_question = bool(re.search(r"\\b(ivy league|university|universit(y|ies)|college|higher education)\\b", query, re.I))
    decision_question = bool(re.search(r"\\b(choos(e|ing)|choice|select(ing|ion)?|decision|what matters|important|factors?)\\b", query, re.I))
    if education_question and decision_question:
        domain_match = bool(_EDUCATION_TERMS & all_terms)
        decision_match = bool(_DECISION_TERMS & all_terms)
        return domain_match and decision_match and (title_hits >= 1 or abstract_hits >= 3)

    # General questions must match multiple substantive terms.
    topic_terms = query_terms - {"how", "many", "much", "people", "person"}
    return bool(topic_terms) and score >= 0.16 and (
        title_hits >= 2 or abstract_hits >= 3
    )


def _plain_abstract(value: str) -> str:
    """Remove JATS/HTML markup while retaining readable text and section labels."""
    value = re.sub(r"</(?:jats:)?(?:title|label)>", " — ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def extract_abstract_findings(query: str, studies: list[StudyRecord]) -> list[dict]:
    """
    Build concise, traceable summaries from the result-oriented sentences in
    study abstracts. These summaries describe what the abstract reports; they
    are not independent verification or population-level survey estimates.
    """
    query_terms = _normalized_terms(query)
    findings: list[dict] = []
    result_signals = {
        "result", "results", "finding", "findings", "found", "showed", "shows",
        "reported", "reports", "increased", "decreased", "higher", "lower",
        "associated", "association", "significant", "majority", "percent",
        "percentage", "participants", "respondents", "concluded", "conclusion",
        "suggest", "suggests", "indicate", "indicates",
    }

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

        # A sentence explicitly marked Results/Findings/Conclusion is a strong
        # candidate. Otherwise rank sentences by result language and topic fit.
        def sentence_score(sentence: str) -> tuple[int, int]:
            terms = _normalized_terms(sentence)
            signal_hits = len(terms & result_signals)
            topic_hits = len(terms & query_terms)
            return (signal_hits, topic_hits)

        labelled = [
            sentence for sentence in sentences
            if re.search(r"\b(results?|findings?|conclusions?)\s*[—:-]", sentence, re.I)
        ]
        ranked = sorted(sentences, key=sentence_score, reverse=True)
        candidates = labelled + [s for s in ranked if s not in labelled]
        selected: list[str] = []
        for sentence in candidates:
            if sentence not in selected:
                selected.append(sentence)
            if len(selected) == 2:
                break

        # Abstracts without a dedicated results sentence can still provide a
        # short overview, but the UI labels it as abstract-based context.
        summary = " ".join(selected).strip()
        if len(summary) > 620:
            summary = summary[:617].rsplit(" ", 1)[0] + "..."
        if not summary:
            continue

        source_url = str(study.locations[0].url) if study.locations else (
            f"https://doi.org/{study.doi}" if study.doi else ""
        )
        findings.append({
            "id": study.doi or source_url or study.title,
            "title": "Abstract-based summary",
            "summary": summary,
            "evidence_text": summary,
            "source_title": study.title,
            "source_url": source_url,
            "publication_year": study.publication_year,
            "evidence_type": "supporting_research",
            "evidence_level": "abstract",
            "interpretation": "Summary of statements in the publication abstract. It is not an independently verified survey result or a population estimate.",
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
            "survey_results": [],
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
        # No survey connector currently supplies validated distributions. Keep
        # this empty until source adapters return question-level survey data.
        "survey_results": [],
        "duplicate_candidates": duplicate_candidates,
        "sources_searched": [adapter.name for adapter in adapters],
        "source_failures": failures,
        "candidate_records_screened": len(candidate_records),
        "relevant_source_records": len(relevant_records),
        "raw_records_found": len(candidate_records),
        "unique_studies": len(studies),
        "abstracts_with_evidence": len(findings),
    }
