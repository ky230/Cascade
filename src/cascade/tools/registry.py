from __future__ import annotations
from typing import Dict, Optional, List
from cascade.tools.base import BaseTool, ToolResult


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        for alias in tool.aliases:
            self._tools[alias] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        seen = set()
        result = []
        for tool in self._tools.values():
            if tool.name not in seen:
                seen.add(tool.name)
                result.append(tool)
        return result

    def get_tool_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.get_input_schema(),
                }
            }
            for tool in self.list_tools() if tool.is_enabled()
        ]

    async def execute(self, name: str, input: dict) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(output=f"Unknown tool: {name}", is_error=True)
        if not await tool.check_permissions(**input):
            return ToolResult(output=f"Permission denied for {name}", is_error=True)
        return await tool.execute(**input)
