import re
import unicodedata
from difflib import SequenceMatcher
from app.sources.base import RawSourceItem


def normalize_title(title: str) -> str:
    """Normalize superficial title differences without discarding meaningful words."""
    value = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    value = doi.strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    return value or None


def exact_identity_key(item: RawSourceItem) -> str | None:
    """Use globally meaningful identifiers; provider-local IDs are not cross-site identity."""
    doi = normalize_doi(item.doi or item.identifiers.get("doi"))
    if doi:
        return f"doi:{doi}"

    for identifier_type in ("pmid", "pmcid", "arxiv", "openalex"):
        identifier = item.identifiers.get(identifier_type)
        if identifier:
            normalized = identifier.strip().lower()
            if identifier_type == "arxiv":
                normalized = re.sub(r"^https?://arxiv\.org/abs/", "", normalized)
            normalized = re.sub(rf"^{identifier_type}:\s*", "", normalized)
            if normalized:
                return f"{identifier_type}:{normalized}"
    return None


def compare_records(left: RawSourceItem, right: RawSourceItem) -> dict[str, float | str | bool]:
    """Score possible duplicates. Similarity is a review signal, not proof."""
    left_key = exact_identity_key(left)
    right_key = exact_identity_key(right)
    if left_key and right_key and left_key == right_key:
        return {"same_study": True, "confidence": 1.0, "reason": "matching_identifier"}

    left_title = normalize_title(left.title)
    right_title = normalize_title(right.title)
    title_score = SequenceMatcher(None, left_title, right_title).ratio()
    year_score = 1.0 if (
        left.publication_year is not None
        and left.publication_year == right.publication_year
    ) else 0.0
    left_authors = {normalize_title(author) for author in left.authors}
    right_authors = {normalize_title(author) for author in right.authors}
    author_score = (
        len(left_authors & right_authors) / len(left_authors | right_authors)
        if left_authors and right_authors and (left_authors | right_authors)
        else 0.0
    )

    # Conservative candidate score. No automatic merge based on title alone.
    confidence = 0.70 * title_score + 0.15 * year_score + 0.15 * author_score
    return {
        "same_study": False,
        "confidence": round(confidence, 4),
        "reason": "possible_duplicate" if confidence >= 0.88 else "not_enough_similarity",
    }
