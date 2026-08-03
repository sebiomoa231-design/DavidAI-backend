"""Google Gemini provider."""
import time
from typing import Dict, List

from david.providers.base import BaseProvider, ProviderResponse, logger


class GeminiProvider(BaseProvider):
    name = "gemini"

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> ProviderResponse:
        start = time.time()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        contents = [
            {"role": "user" if m["role"] != "assistant" else "model", "parts": [{"text": m["content"]}]}
            for m in messages
        ]

        try:
            data = await self._post_json(url, headers={"Content-Type": "application/json"}, json_body={"contents": contents})
            latency_ms = (time.time() - start) * 1000

            candidates = data.get("candidates", [])
            text = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)

            usage = data.get("usageMetadata", {})
            self._record_success(latency_ms)

            return ProviderResponse(
                provider=self.name, model=self.model, text=text, raw=data,
                latency_ms=latency_ms, success=True,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                total_tokens=usage.get("totalTokenCount", 0),
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            self._record_failure(str(e))
            logger.error(f"[gemini] chat failed: {e}")
            return ProviderResponse(
                provider=self.name, model=self.model, text="", raw=None,
                latency_ms=latency_ms, success=False, error=str(e),
            )
