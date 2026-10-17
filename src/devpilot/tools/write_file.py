import os
import tempfile
from pathlib import Path

from ..config import MAX_FILE_SIZE
from .base import BaseTool, ToolResult


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Create or update a text file in workspace"
    risk_level = "medium"
    required_permission = "write_create"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to the workspace root"},
            "content": {"type": "string", "description": "Full text content to write"},
        },
        "required": ["path", "content"],
    }

    def validate_args(self, args: dict) -> bool:
        return (
            isinstance(args.get("path"), str)
            and args["path"].strip()
            and isinstance(args.get("content"), str)
        )

    def execute(self, args: dict, workspace_path: str) -> ToolResult:
        try:
            path = Path(args["path"])
            content = args["content"]
            if len(content) > MAX_FILE_SIZE * 2:  # allow reasonable size
                return ToolResult(success=False, error="Content too large")
            ws = Path(workspace_path).resolve()
            if path.is_absolute():
                rel = path.relative_to(ws) if ws in path.parents or ws == path else None
                if rel is None:
                    return ToolResult(success=False, error="Path outside workspace")
                target = ws / rel
            else:
                target = (ws / path).resolve()
            if not str(target).startswith(str(ws)):
                return ToolResult(success=False, error="Path outside workspace")
            exists = target.exists()
            target.parent.mkdir(parents=True, exist_ok=True)
            # atomic write
            tmp_fd, tmp_path = tempfile.mkstemp(dir=target.parent, prefix=target.name + ".tmp")
            try:
                os.write(tmp_fd, content.encode("utf-8"))
                os.close(tmp_fd)
                os.replace(tmp_path, target)
            except Exception:
                os.close(tmp_fd)
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
            return ToolResult(success=True, data={"created": not exists, "path": str(target.relative_to(ws))}, output=f"Wrote {len(content)} chars")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
