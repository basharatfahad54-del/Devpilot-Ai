import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent / "src"))


import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devpilot.agent import Agent, redact_args
from devpilot.config import ensure_workspace
from devpilot.history.store import HistoryStore
from devpilot.llm.openrouter import OpenRouterProvider
from devpilot.tools.read_file import ReadFileTool
from devpilot.tools.registry import ToolRegistry
from devpilot.tools.safe_terminal import SafeTerminalTool
from devpilot.tools.search_project import SearchProjectTool
from devpilot.tools.write_file import WriteFileTool

app = typer.Typer(help="DevPilot AI - AI developer agent CLI")
console = Console()


def _safe(text: str) -> str:
    """Keep console output printable on legacy Windows code pages (cp1252)."""
    encoding = getattr(console, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
        return text
    except UnicodeEncodeError:
        return text.encode(encoding, errors="replace").decode(encoding)


def _short_args(args: Dict[str, Any], limit: int = 90) -> str:
    text = json.dumps(redact_args(args or {}), ensure_ascii=False)
    return _safe(text if len(text) <= limit else text[: limit - 3] + "...")


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for cls in (ReadFileTool, WriteFileTool, SearchProjectTool, SafeTerminalTool):
        registry.register(cls)
    return registry


def _print_event(event: str, payload: Dict[str, Any]) -> None:
    if event == "task":
        console.print(f"[cyan]Task ID:[/cyan] {payload['task_id'][:8]}")
    elif event == "plan":
        console.print(Panel(_safe(payload["plan"]), title="Plan", border_style="cyan"))
    elif event == "tool_call":
        status = payload.get("status", "")
        args = _short_args(payload.get("args") or {})
        style = {"SUCCESS": "green", "DENIED": "yellow", "BLOCKED": "red"}.get(status, "red")
        mark = {"SUCCESS": "[green]ok[/green]", "DENIED": "[yellow]denied[/yellow]",
                "BLOCKED": "[red]blocked[/red]"}.get(status, "[red]failed[/red]")
        console.print(f"  {mark}  [bold]{payload['tool']}[/bold]({args})")
        result = _safe((payload.get("result") or "").strip())
        if status == "SUCCESS" and result:
            snippet = "\n".join(result.splitlines()[:6])
            console.print(Panel(snippet, border_style=style, padding=(0, 2)))
        elif status != "SUCCESS":
            console.print(f"    [{style}]{payload.get('error') or result}[/{style}]")
    elif event == "final":
        console.print(Panel(_safe(payload["summary"]), title="[green]Completed[/green]", border_style="green"))
    elif event == "error":
        console.print(Panel(_safe(payload["message"]), title="[red]Failed[/red]", border_style="red"))


@app.command()
def run(
    task: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Auto-approve write/execute actions (no prompt)"),
):
    """Run DevPilot AI on a task"""
    ensure_workspace()
    store = HistoryStore()
    provider = OpenRouterProvider()

    def approval_callback(tool_name: str, args: Dict[str, Any], permission: str, risk: str) -> bool:
        console.print(
            Panel(
                f"[bold]{tool_name}[/bold]  (permission: {permission}, risk: {risk})\n"
                f"[dim]{_short_args(args, 400)}[/dim]",
                title="[yellow]Permission required[/yellow]",
                border_style="yellow",
            )
        )
        return typer.confirm("Allow this action?", default=False)

    agent = Agent(
        provider=provider,
        registry=_build_registry(),
        history=store,
        approve_callback=(lambda *_a: True) if yes else approval_callback,
        on_event=_print_event,
    )

    console.print(Panel.fit("DevPilot AI", style="bold blue"))
    console.print(f"[yellow]Task:[/yellow] {task}")
    if not provider.api_key:
        console.print("[red]No OPENROUTER_API_KEY configured - see .env.example[/red]")
        raise typer.Exit(code=1)

    result = agent.run(task)
    if result["status"] != "COMPLETED":
        raise typer.Exit(code=1)


@app.command()
def history(limit: int = 5):
    """Show recent history"""
    store = HistoryStore()
    tasks = store.list_tasks(limit)
    if not tasks:
        console.print("No history found")
        return
    table = Table(title="Recent Tasks")
    table.add_column("Task ID")
    table.add_column("Request")
    table.add_column("Status")
    table.add_column("Start")
    for t in tasks[:limit]:
        req = (t["user_request"][:40] + "...") if len(t["user_request"]) > 40 else t["user_request"]
        table.add_row(t["task_id"][:8], req, t["status"], t["start_time"])
    console.print(table)


@app.command()
def inspect(task_id: str = typer.Argument(None)):
    """Inspect a task"""
    store = HistoryStore()
    if not task_id:
        console.print("Usage: inspect <task_id>")
        return
    task = store.get_task(task_id)
    if not task:
        console.print(f"Task {task_id} not found")
        return
    console.print(Panel(task["user_request"], title="Request"))
    console.print(f"Status: {task['status']}")
    if task.get("plan"):
        console.print(Panel(task["plan"], title="Plan"))
    if task.get("tool_calls"):
        table = Table(title="Tool Calls")
        table.add_column("Tool")
        table.add_column("Args")
        table.add_column("Status")
        table.add_column("Approval")
        table.add_column("ms")
        for tc in task["tool_calls"]:
            table.add_row(
                tc["tool_name"],
                (tc["arguments"] or "")[:60],
                tc["status"],
                tc["approval_decision"] or "-",
                str(tc["duration_ms"]) if tc["duration_ms"] is not None else "-",
            )
        console.print(table)


if __name__ == "__main__":
    app()
