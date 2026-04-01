import asyncio
import os
from cascade.tools.base import BaseTool, ToolResult


class BashTool(BaseTool):
    name = "bash"
    description = "Execute a shell command and return output"

    @property
    def is_destructive(self) -> bool:
        return True

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer", "default": 30},
            },
            "required": ["command"],
        }

    async def execute(self, command: str = "", timeout: int = 30, **kwargs) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = (stdout.decode() + stderr.decode()).strip() or "(no output)"
            return ToolResult(
                output=output,
                is_error=proc.returncode != 0,
                metadata={"exit_code": proc.returncode},
            )
        except asyncio.TimeoutError:
            return ToolResult(output=f"Command timed out after {timeout}s", is_error=True)
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)
