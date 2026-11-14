import httpx

from app.ai.base import StructuredAIProvider, T
from app.ai.schemas import AIInterpretationError


class CloudflareWorkersAIProvider(StructuredAIProvider):
    """Cloudflare Workers AI REST adapter; credentials are read from environment by the factory."""

    def __init__(self, account_id: str, api_token: str, model: str, timeout_seconds: float = 25.0) -> None:
        self.account_id = account_id
        self.api_token = api_token
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate_structured(self, *, system_prompt: str, user_prompt: str, output_model: type[T]) -> T:
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}"
            f"/ai/v1/chat/completions"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": 1200,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            content = body["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            if not isinstance(content, str) or not content.strip():
                raise ValueError("The model returned an empty response.")
            return output_model.model_validate_json(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIInterpretationError(f"Cloudflare Workers AI interpretation failed: {exc}") from exc
