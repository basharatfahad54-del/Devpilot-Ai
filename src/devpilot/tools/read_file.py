from pathlib import Path

from ..config import MAX_FILE_SIZE, MAX_TOOL_OUTPUT
from .base import BaseTool, ToolResult


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read a text file inside the workspace"
    risk_level = "low"
    required_permission = "read"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to the workspace root"}
        },
        "required": ["path"],
    }

    def validate_args(self, args: dict) -> bool:
        return isinstance(args.get("path"), str) and args["path"].strip()

    def execute(self, args: dict, workspace_path: str) -> ToolResult:
        try:
            target_path = Path(args["path"])
            if target_path.is_absolute():
                target_path = target_path.relative_to(workspace_path) if workspace_path in str(target_path) else None
                if target_path is None:
                    return ToolResult(success=False, error="Path outside workspace")
                target_path = Path(workspace_path) / target_path
            else:
                target_path = (Path(workspace_path) / target_path).resolve()
            ws = Path(workspace_path).resolve()
            if not str(target_path).startswith(str(ws)):
                return ToolResult(success=False, error="Path traversal not allowed")

            if not target_path.exists():
                return ToolResult(success=False, error="File not found")
            if target_path.is_dir():
                return ToolResult(success=False, error="Path is a directory")
            if target_path.stat().st_size > MAX_FILE_SIZE:
                return ToolResult(success=False, error="File too large")
            content = target_path.read_text(encoding="utf-8-sig", errors="ignore")
            if len(content) > MAX_TOOL_OUTPUT:
                content = content[:MAX_TOOL_OUTPUT] + "\n... [truncated]"
            return ToolResult(success=True, data={"path": str(target_path.relative_to(ws))}, output=content)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
