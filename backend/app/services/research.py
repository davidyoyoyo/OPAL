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
_OPINION_WORDS = {"like", "likes", "liked", "liking", "love", "loves", "loved", "prefer", "prefers", "preference", "preferences", "support", "favor", "favour", "attitude", "attitudes", "opinion", "opinions", "feel", "feeling", "enjoy", "enjoys", "enjoyed", "interest", "interests", "interested"}
_SURVEY_SIGNALS = {"survey", "poll", "respondent", "respondents", "participant", "participants", "consumer", "consumers", "questionnaire", "sample"}
_PREVALENCE_MEASURE_SIGNALS = {
    "majority", "minority", "most", "half", "one-third", "one-quarter",
}
_EXPLANATORY_SIGNALS = {
    "sensory", "taste", "flavor", "flavour", "texture", "sweetness", "aroma",
    "color", "colour", "creaminess", "acceptance", "acceptability", "liking",
    "hedonic", "organoleptic", "preference", "preferences", "factor", "factors",
    "motivation", "motivations", "reason", "reasons", "purchase", "consumption",
    "quality", "price", "availability", "interest", "interests", "interested",
}
_EDUCATION_TERMS = {"ivy", "league", "university", "universities", "college", "colleges", "student", "students", "education", "admission", "admissions", "campus", "institution", "institutions", "higher"}
_DECISION_TERMS = {"choice", "decision", "factor", "factors", "important", "importance", "criteria", "select", "selection"}


def _topic_aliases(terms: set[str]) -> set[str]:
    """Expand common inflections and a small set of safe topic synonyms."""
    expanded = set(terms)
    for term in terms:
        if len(term) > 4 and term.endswith("ies"):
            expanded.add(term[:-3] + "y")
        elif len(term) > 3 and term.endswith("s") and not term.endswith("ss"):
            expanded.add(term[:-1])

    aliases = {
        "airplane": {"aircraft", "aviation"},
        "airplanes": {"aircraft", "aviation"},
        "aircraft": {"airplane", "aviation"},
        "aviation": {"airplane", "aircraft"},
        "attitude": {"opinion", "view"},
        "attitudes": {"opinion", "view"},
        "opinion": {"attitude", "view"},
        "opinions": {"attitude", "view"},
    }
    for term in tuple(expanded):
        expanded.update(aliases.get(term, set()))
    return expanded


def _normalized_terms(text: str) -> set[str]:
    terms = _terms(text)
    normalized = set(terms)
    if terms & _CHOICE_WORDS:
        normalized.add("choice")
    if terms & {"matters", "matter", "important", "importance"}:
        normalized.add("importance")
    return normalized


def is_prevalence_question(query: str) -> bool:
    return bool(re.search(
        r"\b(how many|what percentage|what percent|how common|how widespread|"
        r"what share|what proportion|what number of)\b",
        query, re.I
    )) or bool(re.search(
        r"\b(people|consumers|adults|respondents)\b.*\b(like|love|prefer|support|favor|favour|enjoy)\b",
        query, re.I
    ))


def classify_relevance(query: str, item: RawSourceItem) -> str | None:
    """Return direct_answer, explanatory_context, or None using question intent.

    For prevalence questions, topical overlap alone is insufficient: direct
    evidence must report a measured opinion, while explanatory studies must
    actually examine consumer preferences or reasons.
    """
    query_terms = _normalized_terms(query)
    if not query_terms:
        return None

    title_terms = _normalized_terms(item.title)
    abstract_text = item.abstract or ""
    abstract_terms = _normalized_terms(abstract_text)
    all_terms = title_terms | abstract_terms

    if is_prevalence_question(query):
        topic_terms = query_terms - _OPINION_WORDS - {
            "people", "person", "consumers", "consumer", "adults", "respondents",
            "how", "many", "much", "common", "widespread", "percentage",
            "percent", "share", "proportion", "number",
        }
        if not topic_terms:
            return None
        topic_match = len(_topic_aliases(topic_terms) & all_terms) >= min(2, len(topic_terms))
        if not topic_match:
            return None

        has_survey_context = bool(_SURVEY_SIGNALS & all_terms)
        has_opinion_outcome = bool(_OPINION_WORDS & all_terms)
        has_reported_measure = (
            bool(_PREVALENCE_MEASURE_SIGNALS & all_terms)
            or bool(re.search(r"\b\d+(?:\.\d+)?\s*%", abstract_text))
            or bool(re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+of\s+(the\s+)?(respondents|participants|consumers)\b", abstract_text, re.I))
            or bool(re.search(r"\b\d+\s+(respondents|participants|consumers)\s+(liked|preferred|supported|favored|favourited|enjoyed)\b", abstract_text, re.I))
        )
        if has_survey_context and has_opinion_outcome and has_reported_measure:
            return "direct_answer"

        has_consumer_research_context = bool(
            {"consumer", "consumers", "respondent", "respondents", "participant",
             "participants", "sensory", "organoleptic", "hedonic", "taste",
             "acceptance", "acceptability"} & all_terms
        )
        has_preference_or_sensory_focus = bool(_EXPLANATORY_SIGNALS & all_terms)
        if has_consumer_research_context and has_preference_or_sensory_focus:
            return "explanatory_context"
        return None

    education_question = bool(re.search(
        r"\b(ivy league|university|universit(y|ies)|college|higher education)\b",
        query, re.I
    ))
    decision_question = bool(re.search(
        r"\b(choos(e|ing)|choice|select(ing|ion)?|decision|what matters|important|factors?)\b",
        query, re.I
    ))
    if education_question and decision_question:
        return "direct_answer" if bool(_EDUCATION_TERMS & all_terms) and bool(_DECISION_TERMS & all_terms) else None

    topic_terms = query_terms - {"how", "many", "much", "people", "person"}
    expanded_topics = _topic_aliases(topic_terms)
    return "direct_answer" if topic_terms and len(expanded_topics & all_terms) >= min(2, len(topic_terms)) else None


def relevance_score(query: str, item: RawSourceItem) -> int:
    """Return a simple deterministic lexical relevance score.

    Kept as a public compatibility helper for callers/tests that need to rank
    candidate records. Question-intent filtering is handled separately by
    classify_relevance; a high topical score alone does not make evidence
    suitable for answering a prevalence question.
    """
    query_terms = _normalized_terms(query)
    if not query_terms:
        return 0

    title_terms = _normalized_terms(item.title)
    abstract_terms = _normalized_terms(item.abstract or "")
    expanded_topics = _topic_aliases(query_terms)

    title_matches = len(expanded_topics & title_terms)
    abstract_matches = len(expanded_topics & abstract_terms)
    return title_matches * 3 + abstract_matches


def is_relevant(query: str, item: RawSourceItem) -> bool:
    return classify_relevance(query, item) is not None

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


async def run_research(query: str, registry: SourceRegistry, *, search_query: str | None = None) -> dict:
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

    # AI may provide a concise topic for provider retrieval; deterministic\n    # relevance screening always uses the user's original question below.\n    request = SourceQuery(query=(search_query or query), limit=100)
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

    relevance_by_title: dict[str, str] = {}
    for item in candidate_records:
        role = classify_relevance(query, item)
        if role is None:
            continue
        # If duplicate provider records share a title, retain the strongest
        # relevance classification rather than whichever provider ran last.
        if relevance_by_title.get(item.title) != "direct_answer" or role == "direct_answer":
            relevance_by_title[item.title] = role
    relevant_records = [
        item for item in candidate_records
        if relevance_by_title.get(item.title) is not None
    ]
    # Direct-answer studies appear before explanatory context in the workspace.
    relevant_records.sort(
        key=lambda item: 0 if relevance_by_title.get(item.title) == "direct_answer" else 1
    )
    studies = group_source_records(relevant_records)
    findings = extract_abstract_findings(query, studies)
    for finding in findings:
        finding["evidence_role"] = relevance_by_title.get(
            finding.get("source_title"), "explanatory_context"
        )
    duplicate_candidates = find_duplicate_candidates(relevant_records)

    return {
        "status": "completed" if relevant_records else "no_results",
        "query": query,
        "studies": [{**study.model_dump(mode="json"), "evidence_role": next((relevance_by_title.get(item.title) for item in relevant_records if item.title == study.title), None)} for study in studies],
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
