import shlex
import subprocess
from pathlib import Path
from typing import Set

from ..config import MAX_TOOL_OUTPUT
from .base import BaseTool, ToolResult

ALLOWED_COMMANDS: Set[str] = {
    "python",
    "python3",
    "py",
    "pytest",
    "pip",
    "pip3",
    "git",
    "dir",
    "ls",
    "findstr",
    "where",
    "echo",
    "cat",
    "type",
    "tree",
    "rg",
    "ruff",
    "black",
    "mypy",
}
BLOCKED = {
    "rm", "del", "rmdir", "rd", "format", "deltree", "diskpart", "shutdown",
    "reboot", "reg", "net", "taskkill", "kill", "pkill", "dd", "mkfs",
    "curl", "wget", "powershell", "pwsh", "cmd", "bash", "sh", "sudo",
    "chmod", "chown", "mklink",
}


class SafeTerminalTool(BaseTool):
    name = "safe_terminal"
    description = "Execute approved commands in workspace"
    risk_level = "medium"
    required_permission = "execute"
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Single command from the allowlist (no shell operators)"}
        },
        "required": ["command"],
    }

    def validate_args(self, args: dict) -> bool:
        if not isinstance(args.get("command"), str):
            return False
        cmd = args["command"].strip()
        if not cmd:
            return False
        if any(ch in cmd for ch in [";", "&&", "||", "|", "`", "$(", "&", ">", "<"]):
            return False
        if "'" in cmd or '"' in cmd and ("-c" in cmd or "eval" in cmd):
            return False
        try:
            parts = shlex.split(cmd)
        except Exception:
            parts = cmd.split()
        if not parts:
            return False
        exe = Path(parts[0]).name.lower()
        stem = Path(exe).stem
        # Denylist wins even when the binary is invoked with an extension
        # (e.g. "powershell.exe" must not slip past the "powershell" entry).
        if exe in BLOCKED or stem in BLOCKED:
            return False
        if exe in ALLOWED_COMMANDS or stem in ALLOWED_COMMANDS:
            return True
        # The agent may run Python scripts it authored; opaque binaries may not.
        if exe.endswith(".py"):
            return True
        return False

    def execute(self, args: dict, workspace_path: str) -> ToolResult:
        try:
            cmd = args["command"].strip()
            try:
                parts = shlex.split(cmd)
            except Exception:
                parts = cmd.split()
            ws = Path(workspace_path).resolve()
            result = subprocess.run(
                parts,
                cwd=str(ws),
                capture_output=True,
                text=True,
                timeout=120,
                shell=False,
            )
            out = (result.stdout + "\n" + result.stderr)
            if len(out) > MAX_TOOL_OUTPUT:
                out = out[:MAX_TOOL_OUTPUT] + "\n... [truncated]"
            return ToolResult(success=result.returncode == 0, data={"exit_code": result.returncode}, output=out)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Command timed out")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
