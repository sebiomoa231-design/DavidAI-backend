"""OpenRouter provider (OpenAI-compatible, multi-model gateway)."""
import time
from typing import Dict, List

from david.providers.base import BaseProvider, ProviderResponse, logger


class OpenRouterProvider(BaseProvider):
    name = "openrouter"

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> ProviderResponse:
        start = time.time()
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://david.local",
            "X-Title": "David AI",
        }
        body = {"model": self.model, "messages": messages, **kwargs}

        try:
            data = await self._post_json(url, headers=headers, json_body=body)
            latency_ms = (time.time() - start) * 1000

            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            self._record_success(latency_ms)

            return ProviderResponse(
                provider=self.name, model=self.model, text=text, raw=data,
                latency_ms=latency_ms, success=True,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            self._record_failure(str(e))
            logger.error(f"[openrouter] chat failed: {e}")
            return ProviderResponse(
                provider=self.name, model=self.model, text="", raw=None,
                latency_ms=latency_ms, success=False, error=str(e),
            )
