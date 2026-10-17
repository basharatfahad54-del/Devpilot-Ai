from abc import ABC, abstractmethod
from typing import Any, Dict


class ToolResult:
    def __init__(self, success: bool, data: Any = None, error: str = "", output: str = ""):
        self.success = success
        self.data = data
        self.error = error
        self.output = output

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "output": self.output,
        }


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    risk_level: str = "low"  # low, medium, high
    required_permission: str = "read"  # read, write_create, write_overwrite, execute, install, destructive
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {},
    }

    @abstractmethod
    def validate_args(self, args: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def execute(self, args: Dict[str, Any], workspace_path: str) -> ToolResult:
        pass
