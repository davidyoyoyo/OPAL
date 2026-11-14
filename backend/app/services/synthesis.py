import re
from typing import Any


_STOPWORDS = {
    "about", "after", "again", "also", "among", "and", "are", "because", "been",
    "before", "being", "between", "both", "but", "can", "could", "did", "does",
    "each", "for", "from", "had", "has", "have", "into", "its", "more", "most",
    "not", "often", "only", "other", "our", "over", "same", "some", "such",
    "than", "that", "the", "their", "them", "then", "there", "these", "they",
    "this", "those", "through", "under", "was", "were", "which", "while",
    "with", "would", "study", "studies", "paper", "research", "article",
    "results", "result", "findings", "finding", "conclusion", "conclusions",
    "aim", "aims", "examines", "examined", "explores", "explored",
}


_RESULT_SIGNALS = {
    "found", "showed", "shows", "suggests", "suggested", "indicates",
    "indicated", "associated", "association", "higher", "lower", "increase",
    "increased", "decrease", "decreased", "difference", "differences",
    "significant", "significantly", "reported", "reports", "participants",
    "respondents", "majority", "minority", "correlation", "effect", "effects",
    "predictor", "predictors", "related", "relationship", "compared",
}


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z][a-z0-9-]{2,}", text.lower())
        if token not in _STOPWORDS
    }


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return [
        part.strip(" \\t\\n.;")
        for part in re.split(r"(?<=[.!?])\\s+(?=[A-Z0-9])", cleaned)
        if len(part.strip()) >= 55
    ]


def build_extractive_synthesis(
    query: str, findings: list[dict[str, Any]], *, max_points: int = 5
) -> dict[str, Any]:
    """Create a transparent, multi-document extractive brief when AI is unavailable.

    It ranks sentences across all abstracts instead of taking the first sentence
    from each paper. Every point remains attached to the exact source record.
    This is deliberately not presented as a pooled or causal conclusion.
    """
    query_terms = _tokens(query)
    candidates: list[dict[str, Any]] = []
    abstract_count = 0

    for finding in findings:
        source_text = str(finding.get("evidence_text") or finding.get("summary") or "")
        sentences = _sentences(source_text)
        if not sentences:
            continue
        abstract_count += 1
        source_id = str(finding.get("id") or finding.get("source_url") or finding.get("source_title") or "")
        for sentence in sentences:
            terms = _tokens(sentence)
            result_hits = len(terms & _RESULT_SIGNALS)
            topic_hits = len(terms & query_terms)
            number_bonus = 1 if re.search(r"\\b\\d+(?:\\.\\d+)?%?\\b", sentence) else 0
            intro_penalty = 2 if re.match(
                r"^(this study|the present study|this paper|the aim|the purpose|we investigate|we examine)",
                sentence, re.I
            ) else 0
            score = (2 * result_hits) + topic_hits + number_bonus - intro_penalty
            if score <= 0:
                continue
            candidates.append({
                "text": sentence[:500],
                "source_ids": [source_id] if source_id else [],
                "source_title": finding.get("source_title"),
                "source_url": finding.get("source_url"),
                "publication_year": finding.get("publication_year"),
                "score": score,
            })

    # First pass: favour coverage across distinct studies. Second pass fills
    # remaining slots only when a source has another genuinely useful sentence.
    candidates.sort(key=lambda item: (item["score"], len(item["text"])), reverse=True)
    selected: list[dict[str, Any]] = []
    used_sources: set[str] = set()
    used_sentences: set[str] = set()

    for candidate in candidates:
        source_id = candidate["source_ids"][0] if candidate["source_ids"] else ""
        normalized = re.sub(r"[^a-z0-9]+", " ", candidate["text"].lower()).strip()
        if source_id in used_sources or normalized in used_sentences:
            continue
        selected.append(candidate)
        if source_id:
            used_sources.add(source_id)
        used_sentences.add(normalized)
        if len(selected) >= max_points:
            break

    for candidate in candidates:
        if len(selected) >= max_points:
            break
        normalized = re.sub(r"[^a-z0-9]+", " ", candidate["text"].lower()).strip()
        if normalized in used_sentences:
            continue
        selected.append(candidate)
        used_sentences.add(normalized)

    study_count = len(findings)
    overview = (
        f"OPAL found {study_count} relevant scholarly record"
        f"{'' if study_count == 1 else 's'}; {abstract_count} "
        f"{'contains' if abstract_count == 1 else 'contain'} usable abstract text. "
        "The points below are selected from result-oriented passages across the available "
        "abstracts, with each passage linked to its study. They are not a pooled estimate, "
        "a ranking of causes, or a representative measure of public opinion."
    )
    return {
        "mode": "extractive_fallback",
        "overview": overview,
        "overview_source_ids": [
            str(item.get("id") or item.get("source_url") or item.get("source_title") or "")
            for item in findings[:20]
            if item.get("id") or item.get("source_url") or item.get("source_title")
        ],
        "key_points": selected,
        "limitations": [
            "Abstracts are summaries written by the study authors; full methods and results may not be available here.",
            "Different studies may use different populations, measures, dates and methods, so their findings should not be treated as one combined sample.",
            "No survey response distributions are currently connected; no public-opinion percentages are inferred from these papers.",
        ],
    }
