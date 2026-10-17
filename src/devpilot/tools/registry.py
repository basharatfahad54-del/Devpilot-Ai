from typing import Dict, List, Type

from .base import BaseTool, ToolResult


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._instances: Dict[str, BaseTool] = {}

    def register(self, tool_cls: Type[BaseTool]):
        instance = tool_cls()
        self._tools[instance.name] = tool_cls
        self._instances[instance.name] = instance

    def get(self, name: str) -> BaseTool:
        if name not in self._instances:
            raise ValueError(f"Tool {name} not found")
        return self._instances[name]

    def list(self) -> Dict[str, Dict[str, str]]:
        result = {}
        for name, tool in self._instances.items():
            result[name] = {
                "name": name,
                "description": tool.description,
                "risk_level": tool.risk_level,
                "required_permission": tool.required_permission,
            }
        return result

    def openai_tools(self) -> List[Dict]:
        """Tools formatted for an OpenAI-compatible function-calling API."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._instances.values()
        ]

    def execute(self, name: str, args: Dict, workspace_path: str) -> ToolResult:
        tool = self.get(name)
        if not tool.validate_args(args):
            return ToolResult(success=False, error="Invalid arguments")
        return tool.execute(args, workspace_path)
