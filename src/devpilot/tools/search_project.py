import os
from pathlib import Path

from ..config import MAX_FILE_SIZE, MAX_SEARCH_RESULTS
from .base import BaseTool, ToolResult

EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", "env", "node_modules", ".pytest_cache", ".mypy_cache", "build", "dist"}


class SearchProjectTool(BaseTool):
    name = "search_project"
    description = "Search project files for text query"
    risk_level = "low"
    required_permission = "read"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text substring to search for"}
        },
        "required": ["query"],
    }

    def validate_args(self, args: dict) -> bool:
        return isinstance(args.get("query"), str) and args["query"].strip()

    def execute(self, args: dict, workspace_path: str) -> ToolResult:
        try:
            query = args["query"]
            ws = Path(workspace_path).resolve()
            matches = []
            count = 0
            for root, dirs, files in os.walk(ws):
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                for fname in files:
                    if count > MAX_SEARCH_RESULTS * 5:
                        break
                    fpath = Path(root) / fname
                    try:
                        if fpath.stat().st_size > MAX_FILE_SIZE:
                            continue
                    except OSError:
                        continue
                    if fname in {".env", ".env.local", "id_rsa", "id_ed25519"}:
                        continue
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                    except (OSError, UnicodeDecodeError):
                        continue
                    if query in content:
                        rel = fpath.relative_to(ws)
                        for i, line in enumerate(content.splitlines(), 1):
                            if query in line and len(matches) < MAX_SEARCH_RESULTS:
                                matches.append(f"{rel}:{i}: {line}")
                        count += 1
                if len(matches) >= MAX_SEARCH_RESULTS:
                    break
            return ToolResult(success=True, data={"matches": len(matches)}, output="\n".join(matches) if matches else "No matches found")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
