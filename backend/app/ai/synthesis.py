from pydantic import BaseModel, ConfigDict, Field


class EvidenceSynthesisPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=20, max_length=500)
    source_ids: list[str] = Field(min_length=1, max_length=8)


class EvidenceSynthesis(BaseModel):
    """A concise cross-study brief with explicit links back to its evidence."""

    model_config = ConfigDict(extra="forbid")

    overview: str = Field(min_length=20, max_length=1200)
    key_points: list[EvidenceSynthesisPoint] = Field(default_factory=list, max_length=5)
    limitations: list[str] = Field(default_factory=list, max_length=8)
