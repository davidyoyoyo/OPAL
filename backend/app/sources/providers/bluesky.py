import re
import time
from datetime import datetime
from urllib.parse import quote

import httpx

from app.sources.discussion_base import DiscussionQuery, DiscussionRecord


class BlueskyAdapter:
    """Search public Bluesky posts for a single user-initiated research query.

    This uses the public AppView search endpoint without credentials. It does
    not crawl the network or paginate bulk archives.
    """

    name = "bluesky"
    description = "Public Bluesky posts and discussion matching the research topic"
    endpoint = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"

    _STOPWORDS = {
        "how", "many", "much", "people", "person", "do", "does", "like",
        "likes", "love", "loves", "what", "percentage", "percent", "is",
        "are", "the", "a", "an", "of", "to", "about", "think", "opinion",
        "opinions", "public", "everyone", "anyone",
    }

    def __init__(self, cache_ttl: float = 600.0, timeout_seconds: float = 20.0) -> None:
        self.cache_ttl = cache_ttl
        self.timeout_seconds = timeout_seconds
        self._cache: dict[str, tuple[float, list[DiscussionRecord]]] = {}

    @classmethod
    def build_search_query(cls, topic: str) -> str:
        terms = [
            token.strip(".,!?;:\"'()[]{}")
            for token in re.findall(r"[^\s]+", topic.lower())
        ]
        cleaned = [term for term in terms if term and term not in cls._STOPWORDS]
        return " ".join(cleaned) or topic.strip()

    @staticmethod
    def parse_posts(payload: dict, limit: int = 40) -> list[DiscussionRecord]:
        records: list[DiscussionRecord] = []
        seen: set[str] = set()
        for result in payload.get("posts", [])[:limit]:
            post = result.get("post") or {}
            record = post.get("record") or {}
            text = str(record.get("text") or "").strip()
            uri = str(post.get("uri") or "")
            if not text or not uri or uri in seen:
                continue
            seen.add(uri)

            # at://did:plc:.../app.bsky.feed.post/rkey
            rkey = uri.rsplit("/", 1)[-1]
            handle = str((post.get("author") or {}).get("handle") or "")
            if not handle or not rkey:
                continue
            try:
                published = datetime.fromisoformat(
                    str(record.get("createdAt") or post.get("indexedAt")).replace("Z", "+00:00")
                )
            except (TypeError, ValueError):
                published = None

            records.append(DiscussionRecord(
                id=uri,
                platform="Bluesky",
                title="Public Bluesky post",
                text=text[:4000],
                source_url=f"https://bsky.app/profile/{handle}/post/{rkey}",
                published_at=published,
                like_count=post.get("likeCount"),
                reply_count=post.get("replyCount"),
                repost_count=post.get("repostCount"),
            ))
        return records

    async def search(self, query: DiscussionQuery) -> list[DiscussionRecord]:
        search_text = self.build_search_query(query.topic)
        cache_key = search_text.casefold()
        cached = self._cache.get(cache_key)
        now = time.monotonic()
        if cached and now - cached[0] < self.cache_ttl:
            return list(cached[1])

        headers = {"User-Agent": "OPALResearch/0.4 (user-initiated public discussion search)"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
            response = await client.get(
                self.endpoint,
                params={"q": search_text, "limit": min(query.limit, 100), "sort": "top"},
            )
            response.raise_for_status()
            payload = response.json()

        records = self.parse_posts(payload, query.limit)
        self._cache[cache_key] = (time.monotonic(), records)
        return list(records)
