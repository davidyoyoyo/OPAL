from app.sources.base import SourceAdapter


class SourceRegistry:
    """Central connector registry. Adding a provider should not change the engine."""

    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        key = adapter.name.strip().lower()
        if not key:
            raise ValueError("A source adapter must have a name.")
        if key in self._adapters:
            raise ValueError(f"Source adapter '{key}' is already registered.")
        self._adapters[key] = adapter

    def get_all(self) -> list[SourceAdapter]:
        return list(self._adapters.values())

    def public_catalog(self) -> list[dict[str, str]]:
        return [
            {"name": adapter.name, "description": adapter.description}
            for adapter in self.get_all()
        ]


source_registry = SourceRegistry()
