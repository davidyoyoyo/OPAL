from app.sources.discussion_base import DiscussionQuery, DiscussionRecord
from app.sources.discussion_registry import DiscussionSourceRegistry
from app.sources.providers.bluesky import BlueskyAdapter


def test_discussion_registry_registers_independent_adapters():
    class FakeAdapter:
        name = "fake"
        description = "fake discussions"

        async def search(self, query):
            return []

    registry = DiscussionSourceRegistry()
    registry.register(FakeAdapter())
    assert registry.public_catalog()[0]["evidence_type"] == "expressed_opinion"


def test_discussion_registry_rejects_duplicate_names():
    class FakeAdapter:
        name = "same"
        description = "fake"

        async def search(self, query):
            return []

    registry = DiscussionSourceRegistry()
    registry.register(FakeAdapter())
    try:
        registry.register(FakeAdapter())
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate provider name should be rejected")


def test_bluesky_search_query_removes_question_framing():
    assert BlueskyAdapter.build_search_query("How many people like JoJo?") == "jojo"


def test_bluesky_parser_normalizes_public_posts_without_author_identity():
    payload = {
        "posts": [{
            "post": {
                "uri": "at://did:plc:example/app.bsky.feed.post/abc123",
                "record": {"text": "JoJo is fantastic", "createdAt": "2026-11-14T12:00:00Z"},
                "author": {"handle": "example.bsky.social", "displayName": "Private Display Name"},
                "likeCount": 8,
                "replyCount": 2,
                "repostCount": 1,
            }
        }]
    }
    items = BlueskyAdapter.parse_posts(payload)
    assert len(items) == 1
    assert items[0].text == "JoJo is fantastic"
    assert items[0].source_url.endswith("/abc123")
    assert "Private Display Name" not in items[0].model_dump_json()


def test_discussion_record_requires_a_source_url():
    try:
        DiscussionRecord(
            id="x", platform="test", title="Post", text="Hello world",
            source_url="not a url",
        )
    except Exception:
        pass
    else:
        raise AssertionError("Invalid source URL should be rejected")


def test_discussion_query_is_bounded():
    query = DiscussionQuery(question="What do people think about JoJo?", topic="JoJo")
    assert query.limit == 40
