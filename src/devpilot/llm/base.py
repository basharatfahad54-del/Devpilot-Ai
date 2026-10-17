from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMResponse:
    def __init__(self, content: str = "", tool_calls: Optional[List[Dict[str, Any]]] = None, raw: Dict[str, Any] = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.raw = raw or {}


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None, **kwargs) -> LLMResponse:
        pass
