import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .config import MAX_STEPS, MAX_TOOL_OUTPUT, REQUIRE_APPROVAL, WORKSPACE_DIR
from .history.store import HistoryStore
from .llm.base import BaseLLMProvider
from .planner import Planner
from .security.permissions import ApprovalManager
from .tools.registry import ToolRegistry

SYSTEM_PROMPT = (
    "You are DevPilot AI, an AI developer agent working inside a sandboxed workspace. "
    "Think step by step, use the provided tools to inspect and modify files, and keep "
    "answers concise. Never attempt commands outside the tool interface."
)

# tool_name, args, permission, risk_level -> approved?
ApprovalCallback = Callable[[str, Dict[str, Any], str, str], bool]
# event name, payload -> None
EventHandler = Callable[[str, Dict[str, Any]], None]

SENSITIVE_KEY_HINTS = ("api_key", "apikey", "token", "secret", "password", "authorization")


def redact_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """Strip secret-looking values before an argument dict is written to history."""
    redacted: Dict[str, Any] = {}
    for key, value in args.items():
        if any(hint in key.lower() for hint in SENSITIVE_KEY_HINTS):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_args(value)
        else:
            redacted[key] = value
    return redacted


def _parse_tool_call(tc: Dict[str, Any]) -> tuple:
    fn = tc.get("function") or {}
    name = fn.get("name") or tc.get("name") or ""
    raw = fn.get("arguments", "{}")
    try:
        args = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except (json.JSONDecodeError, TypeError):
        args = None
    return name, args, tc.get("id", "")


class Agent:
    """The agent loop: plan -> LLM -> tool call -> permission gate -> execute -> log -> re-plan."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        registry: Optional[ToolRegistry] = None,
        history: Optional[HistoryStore] = None,
        approval_manager: Optional[ApprovalManager] = None,
        approve_callback: Optional[ApprovalCallback] = None,
        on_event: Optional[EventHandler] = None,
        workspace: Optional[str] = None,
        max_steps: Optional[int] = None,
        planner: Optional[Planner] = None,
    ):
        self.provider = provider
        self.registry = registry or ToolRegistry()
        self.history = history or HistoryStore()
        self.approvals = approval_manager or ApprovalManager(require_approval=REQUIRE_APPROVAL)
        self.approve_callback = approve_callback
        self.on_event = on_event
        self.workspace = str(workspace or WORKSPACE_DIR)
        self.max_steps = max_steps or MAX_STEPS
        self.planner = planner or Planner()

    def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        if not self.on_event:
            return
        try:
            self.on_event(event, payload)
        except Exception:
            # A presentation-layer failure must never abort the agent loop
            # or leave a task stuck mid-run.
            pass

    def run(self, task: str) -> Dict[str, Any]:
        task_id = self.history.create_task(task, status="PLANNING")
        self._emit("task", {"task_id": task_id, "request": task})

        plan = self.planner.create_plan_text(task, self.provider)
        self.history.update_task(task_id, plan=plan, status="EXECUTING")
        self._emit("plan", {"plan": plan})

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}\n\nPlan:\n{plan}"},
        ]
        steps: List[Dict[str, Any]] = []
        tool_calls_made = 0

        for _step in range(1, self.max_steps + 1):
            resp = self.provider.generate(messages, tools=self.registry.openai_tools())
            content = (resp.content or "").strip()

            if not resp.tool_calls and content.startswith("Error:"):
                self._fail(task_id, content, steps)
                return {"task_id": task_id, "status": "FAILED", "summary": content, "plan": plan, "steps": steps}

            if not resp.tool_calls:
                summary = content or "Done (no final message from model)."
                self.history.update_task(
                    task_id, status="COMPLETED", end_time=datetime.utcnow(), final_summary=summary
                )
                self._emit("final", {"summary": summary})
                return {"task_id": task_id, "status": "COMPLETED", "summary": summary, "plan": plan, "steps": steps}

            messages.append(
                {"role": "assistant", "content": resp.content or "", "tool_calls": resp.tool_calls}
            )

            for tc in resp.tool_calls:
                if tool_calls_made >= 20:
                    break
                tool_calls_made += 1
                step = self._handle_tool_call(task_id, tc, messages)
                steps.append(step)

        summary = f"Stopped: reached max steps ({self.max_steps}) without a final answer."
        self._fail(task_id, summary, steps)
        return {"task_id": task_id, "status": "FAILED", "summary": summary, "plan": plan, "steps": steps}

    def _handle_tool_call(self, task_id: str, tc: Dict[str, Any], messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        name, args, tc_id = _parse_tool_call(tc)
        step: Dict[str, Any] = {"tool": name, "args": args, "approval": "not_required"}

        def record(status: str, result_text: str, error: str = "", duration_ms: int = 0) -> Dict[str, Any]:
            step.update({"status": status, "result": result_text, "error": error, "duration_ms": duration_ms})
            self.history.add_tool_call(
                task_id,
                name,
                redact_args(args or {}),
                status,
                result=result_text[:10000],
                error=error[:5000] if error else None,
                duration_ms=duration_ms,
                approval_decision=step.get("approval"),
            )
            self._emit("tool_call", dict(step))
            messages.append({"role": "tool", "tool_call_id": tc_id, "content": result_text[:MAX_TOOL_OUTPUT]})
            return step

        if args is None:
            return record("FAILED", "Error: malformed tool arguments (expected JSON)")

        try:
            tool = self.registry.get(name)
        except ValueError:
            return record("FAILED", f"Error: unknown tool '{name}'")

        if self.approvals.requires_approval(tool.required_permission, tool.risk_level):
            approved = False
            if self.approve_callback is not None:
                approved = self.approve_callback(name, args, tool.required_permission, tool.risk_level)
            step["approval"] = "approved" if approved else "denied"
            if not approved:
                return record("DENIED", "User denied this action. Choose another approach.")

        if not tool.validate_args(args):
            return record("BLOCKED", f"Blocked by safety policy: '{name}' rejected the arguments (invalid or not permitted)")

        started = time.monotonic()
        try:
            result = tool.execute(args, self.workspace)
        except Exception as exc:  # tool bugs must not kill the loop
            duration_ms = int((time.monotonic() - started) * 1000)
            return record("FAILED", f"Error: {exc}", error=str(exc), duration_ms=duration_ms)
        duration_ms = int((time.monotonic() - started) * 1000)

        if result.success:
            text = result.output or json.dumps(result.data or {})
            return record("SUCCESS", text, duration_ms=duration_ms)
        return record("FAILED", f"Error: {result.error}", error=result.error, duration_ms=duration_ms)

    def _fail(self, task_id: str, summary: str, steps: List[Dict[str, Any]]) -> None:
        self.history.update_task(
            task_id, status="FAILED", end_time=datetime.utcnow(), final_summary=summary
        )
        self._emit("error", {"message": summary})
