from app.sources.discussion_base import DiscussionSourceAdapter


class DiscussionSourceRegistry:
    """Independent registry for public discussion platforms."""

    def __init__(self) -> None:
        self._adapters: dict[str, DiscussionSourceAdapter] = {}

    def register(self, adapter: DiscussionSourceAdapter) -> None:
        key = adapter.name.strip().lower()
        if not key:
            raise ValueError("A discussion source must have a name.")
        if key in self._adapters:
            raise ValueError(f"Discussion source '{key}' is already registered.")
        self._adapters[key] = adapter

    def get_all(self) -> list[DiscussionSourceAdapter]:
        return list(self._adapters.values())

    def public_catalog(self) -> list[dict[str, str]]:
        return [
            {"name": adapter.name, "description": adapter.description, "evidence_type": "expressed_opinion"}
            for adapter in self._adapters.values()
        ]


discussion_registry = DiscussionSourceRegistry()
