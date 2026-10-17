import json
import tempfile
from pathlib import Path

from src.devpilot.agent import Agent
from src.devpilot.history.store import HistoryStore
from src.devpilot.llm.base import BaseLLMProvider, LLMResponse
from src.devpilot.tools.read_file import ReadFileTool
from src.devpilot.tools.registry import ToolRegistry
from src.devpilot.tools.safe_terminal import SafeTerminalTool
from src.devpilot.tools.search_project import SearchProjectTool
from src.devpilot.tools.write_file import WriteFileTool


class FakeProvider(BaseLLMProvider):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, messages, tools=None, **kwargs):
        self.calls.append({"messages": messages, "tools": tools})
        if self.responses:
            return self.responses.pop(0)
        return LLMResponse(content="Error: no scripted response left")


def tool_call(name, args, call_id="call-1"):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def plan_response():
    """The planner makes one LLM call before the agent loop starts."""
    return LLMResponse(content="1. Read the file\n2. Report findings")


def build_agent(tmp, provider, approve_callback=None):
    ws = Path(tmp) / "ws"
    ws.mkdir(exist_ok=True)
    store = HistoryStore(Path(tmp) / "history.db")
    registry = ToolRegistry()
    for cls in (ReadFileTool, WriteFileTool, SearchProjectTool, SafeTerminalTool):
        registry.register(cls)
    agent = Agent(
        provider=provider,
        registry=registry,
        history=store,
        approve_callback=approve_callback,
        workspace=str(ws),
    )
    return agent, store, ws


def test_agent_executes_tool_and_completes():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "ws").mkdir()
        (Path(tmp) / "ws" / "hello.txt").write_text("Hello DevPilot")
        provider = FakeProvider(
            [
                plan_response(),
                LLMResponse(tool_calls=[tool_call("read_file", {"path": "hello.txt"})]),
                LLMResponse(content="File says Hello DevPilot."),
            ]
        )
        agent, store, ws = build_agent(tmp, provider)
        result = agent.run("read hello.txt")
        assert result["status"] == "COMPLETED"
        assert result["steps"][0]["status"] == "SUCCESS"
        assert "Hello DevPilot" in result["steps"][0]["result"]
        task = store.get_task(result["task_id"])
        assert task["status"] == "COMPLETED"
        assert len(task["tool_calls"]) == 1
        assert task["tool_calls"][0]["approval_decision"] == "not_required"
        assert provider.calls[1]["tools"][0]["function"]["name"] == "read_file"


def test_write_approved_by_user_executes():
    with tempfile.TemporaryDirectory() as tmp:
        provider = FakeProvider(
            [
                plan_response(),
                LLMResponse(tool_calls=[tool_call("write_file", {"path": "calc.py", "content": "x = 1"})]),
                LLMResponse(content="Created calc.py."),
            ]
        )
        agent, store, ws = build_agent(tmp, provider, approve_callback=lambda *a: True)
        result = agent.run("create calc.py")
        assert result["status"] == "COMPLETED"
        assert result["steps"][0]["status"] == "SUCCESS"
        assert result["steps"][0]["approval"] == "approved"
        assert (ws / "calc.py").read_text() == "x = 1"


def test_write_denied_by_user_skips_execution():
    with tempfile.TemporaryDirectory() as tmp:
        provider = FakeProvider(
            [
                plan_response(),
                LLMResponse(tool_calls=[tool_call("write_file", {"path": "evil.py", "content": "nope"})]),
                LLMResponse(content="Understood, skipping the write."),
            ]
        )
        agent, store, ws = build_agent(tmp, provider, approve_callback=lambda *a: False)
        result = agent.run("write something")
        assert result["steps"][0]["status"] == "DENIED"
        assert result["steps"][0]["approval"] == "denied"
        assert not (ws / "evil.py").exists()
        task = store.get_task(result["task_id"])
        assert task["tool_calls"][0]["approval_decision"] == "denied"


def test_blocked_command_rejected_by_policy():
    with tempfile.TemporaryDirectory() as tmp:
        provider = FakeProvider(
            [
                plan_response(),
                LLMResponse(tool_calls=[tool_call("safe_terminal", {"command": "rm -rf /"})]),
                LLMResponse(content="Command rejected, continuing."),
            ]
        )
        agent, store, ws = build_agent(tmp, provider, approve_callback=lambda *a: True)
        result = agent.run("clean up")
        assert result["steps"][0]["status"] == "BLOCKED"
        assert "safety policy" in result["steps"][0]["result"]


def test_llm_error_fails_gracefully():
    with tempfile.TemporaryDirectory() as tmp:
        provider = FakeProvider([plan_response(), LLMResponse(content="Error: Request timeout")])
        agent, store, ws = build_agent(tmp, provider)
        result = agent.run("do something")
        assert result["status"] == "FAILED"
        assert "timeout" in result["summary"]
        assert store.get_task(result["task_id"])["status"] == "FAILED"


def test_missing_approval_callback_denies_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        provider = FakeProvider(
            [
                plan_response(),
                LLMResponse(tool_calls=[tool_call("write_file", {"path": "a.txt", "content": "hi"})]),
                LLMResponse(content="Skipped."),
            ]
        )
        agent, store, ws = build_agent(tmp, provider, approve_callback=None)
        result = agent.run("write a.txt")
        assert result["steps"][0]["status"] == "DENIED"
        assert not (ws / "a.txt").exists()
