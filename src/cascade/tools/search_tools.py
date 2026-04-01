import os
import glob as glob_mod
from cascade.tools.base import BaseTool, ToolResult


class GrepTool(BaseTool):
    name = "grep"
    description = "Search for a pattern in files using ripgrep-style output"

    @property
    def is_read_only(self) -> bool:
        return True

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "default": "."},
                "include": {"type": "string", "default": ""},
            },
            "required": ["pattern"],
        }

    async def execute(self, pattern: str = "", path: str = ".", include: str = "", **kwargs) -> ToolResult:
        import asyncio
        cmd = f"grep -rnI --color=never '{pattern}' {path}"
        if include:
            cmd = f"grep -rnI --color=never --include='{include}' '{pattern}' {path}"
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            output = stdout.decode().strip()
            if not output:
                return ToolResult(output="No matches found")
            # Limit output
            lines = output.split("\n")
            if len(lines) > 50:
                output = "\n".join(lines[:50]) + f"\n... ({len(lines) - 50} more matches)"
            return ToolResult(output=output)
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)


class GlobTool(BaseTool):
    name = "glob"
    description = "Find files matching a glob pattern"

    @property
    def is_read_only(self) -> bool:
        return True

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
            },
            "required": ["pattern"],
        }

    async def execute(self, pattern: str = "", **kwargs) -> ToolResult:
        try:
            matches = sorted(glob_mod.glob(pattern, recursive=True))
            if not matches:
                return ToolResult(output="No files matched")
            output = "\n".join(matches[:100])
            if len(matches) > 100:
                output += f"\n... ({len(matches) - 100} more files)"
            return ToolResult(output=output, metadata={"count": len(matches)})
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)
