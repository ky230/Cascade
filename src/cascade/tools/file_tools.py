import os
from cascade.tools.base import BaseTool, ToolResult


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Read the contents of a file"

    @property
    def is_read_only(self) -> bool:
        return True

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "default": 1},
                "end_line": {"type": "integer", "default": -1},
            },
            "required": ["path"],
        }

    async def execute(self, path: str = "", start_line: int = 1, end_line: int = -1, **kwargs) -> ToolResult:
        try:
            abs_path = os.path.abspath(path)
            if not os.path.isfile(abs_path):
                return ToolResult(output=f"File not found: {path}", is_error=True)

            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if end_line == -1:
                end_line = len(lines)

            start_line = max(1, start_line)
            end_line = min(len(lines), end_line)
            selected = lines[start_line - 1:end_line]

            content = "".join(selected)
            return ToolResult(
                output=content,
                metadata={"path": abs_path, "total_lines": len(lines)},
            )
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)


class FileWriteTool(BaseTool):
    name = "file_write"
    description = "Create or overwrite a file with content"

    @property
    def is_destructive(self) -> bool:
        return True

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        }

    async def execute(self, path: str = "", content: str = "", **kwargs) -> ToolResult:
        try:
            abs_path = os.path.abspath(path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(
                output=f"Wrote {len(content)} bytes to {path}",
                metadata={"path": abs_path, "bytes": len(content)},
            )
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)
