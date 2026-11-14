from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class StructuredAIProvider(ABC):
    """Provider-neutral interface. Provider SDKs stay outside the research engine."""

    @abstractmethod
    async def generate_structured(self, *, system_prompt: str, user_prompt: str, output_model: type[T]) -> T:
        raise NotImplementedError
