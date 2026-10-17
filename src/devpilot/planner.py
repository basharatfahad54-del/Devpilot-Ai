from dataclasses import dataclass
from typing import List, Optional

from .llm.base import BaseLLMProvider

PLAN_SYSTEM_PROMPT = (
    "You are a software planning assistant. Given a development request, "
    "reply with a concise numbered plan (3-6 steps). No preamble, no code."
)


@dataclass
class PlanStep:
    step_number: int
    description: str
    tool: str = ""


class Planner:
    """Generates a step-by-step plan for a task.

    Uses the LLM when a provider is supplied; falls back to a deterministic
    skeleton plan when no provider is available or the LLM call fails.
    """

    def create_plan(self, request: str) -> List[PlanStep]:
        return [
            PlanStep(1, f"Analyze request: {request}"),
            PlanStep(2, "Search/review existing code"),
            PlanStep(3, "Implement the solution"),
            PlanStep(4, "Verify with tests"),
        ]

    def create_plan_text(self, request: str, provider: Optional[BaseLLMProvider] = None) -> str:
        fallback = "\n".join(f"{s.step_number}. {s.description}" for s in self.create_plan(request))
        if provider is None:
            return fallback
        try:
            resp = provider.generate(
                [
                    {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                    {"role": "user", "content": request},
                ]
            )
        except Exception:
            return fallback
        content = (resp.content or "").strip()
        if not content or content.startswith("Error:"):
            return fallback
        return content
