import time
from typing import Any, Dict, List, Optional

import httpx

from ..config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    REQUEST_TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF,
)
from .base import BaseLLMProvider, LLMResponse


class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or OPENROUTER_MODEL
        self.base_url = base_url or OPENROUTER_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/basharatfahad54-del/Devpilot-Ai",
            "X-Title": "DevPilot AI",
        }

    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None, **kwargs) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(content="Error: No API key configured. Set OPENROUTER_API_KEY in .env", tool_calls=[])

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        last_error = None
        for attempt in range(RETRY_ATTEMPTS):
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                    resp = client.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload)
                    if resp.status_code == 401:
                        return LLMResponse(content="Authentication failed: Invalid API key", tool_calls=[])
                    if resp.status_code == 429:
                        time.sleep(RETRY_BACKOFF * (attempt + 1))
                        last_error = "Rate limited"
                        continue
                    if resp.status_code >= 500:
                        time.sleep(RETRY_BACKOFF * (attempt + 1))
                        last_error = f"Server error {resp.status_code}"
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    choice = data.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    content = message.get("content", "") or ""
                    tool_calls = message.get("tool_calls") or []
                    return LLMResponse(content=content, tool_calls=tool_calls, raw=data)
            except httpx.TimeoutException:
                last_error = "Request timeout"
                time.sleep(RETRY_BACKOFF * (attempt + 1))
            except Exception as e:
                last_error = str(e)
                time.sleep(RETRY_BACKOFF * (attempt + 1))
        return LLMResponse(content=f"Error: {last_error}", tool_calls=[])
