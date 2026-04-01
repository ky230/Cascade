# Phase 4: Zod-Equivalent Tool System Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish type-safe tool execution (Pydantic equivalent of Zod) and implement a subset of 6 critical tools (Bash, Read, Write, Edit, Grep, Glob) mirroring Claude Code.
**Architecture:** `BaseTool` defines the abstract interface. `ToolRegistry` handles dispatch and JSON schema aggregation. Individual tool implementations inherit from `BaseTool`.
**Tech Stack:** `pydantic`, `asyncio`, `os`, `subprocess`.

---

### Task 4.1: BaseTool and Tool Registry

**Files:**
- Rewrite: `src/cascade/tools/base.py`
- Create: `src/cascade/tools/registry.py`
- Create: `tests/test_tools_registry.py`

**Step 1: Write the failing test**

```python
# Create tests/test_tools_registry.py
import pytest
from cascade.tools.registry import ToolRegistry
from cascade.tools.base import BaseTool, ToolResult

class MockTool(BaseTool):
    name = "mock"
    description = "Mock tool"
    def get_input_schema(self): return {"type": "object", "properties": {"msg": {"type": "string"}}}
    async def execute(self, msg: str = "", **kw) -> ToolResult:
        return ToolResult(output=msg)

def test_registry_registration():
    reg = ToolRegistry()
    reg.register(MockTool())
    
    assert reg.get("mock") is not None
    schemas = reg.get_tool_schemas()
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "mock"

@pytest.mark.asyncio
async def test_registry_execution():
    reg = ToolRegistry()
    reg.register(MockTool())
    result = await reg.execute("mock", {"msg": "hello context"})
    assert result.output == "hello context"
    assert not result.is_error
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools_registry.py -v`
Expected: FAIL (missing `ToolRegistry`)

**Step 3: Write minimal implementation**

```python
# Rewrite src/cascade/tools/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class ToolResult:
    output: str
    is_error: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    def aliases(self) -> list[str]: return []

    @property
    def is_read_only(self) -> bool: return False

    @property
    def is_destructive(self) -> bool: return False

    def is_enabled(self) -> bool: return True

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult: ...

    @abstractmethod
    def get_input_schema(self) -> dict: ...

    async def check_permissions(self, **kwargs: Any) -> bool: return True

    def user_facing_name(self, input: dict | None = None) -> str: return self.name
```

```python
# Create src/cascade/tools/registry.py
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/tools tests/test_tools_registry.py
git commit -m "feat(tools): implement typed BaseTool and ToolRegistry"
```

---

### Task 4.2: Implement BashTool

**Files:**
- Create: `src/cascade/tools/bash_tool.py`
- Create: `tests/test_bash_tool.py`

**Step 1: Write the failing test**

```python
# Create tests/test_bash_tool.py
import pytest
from cascade.tools.bash_tool import BashTool

@pytest.mark.asyncio
async def test_bash_echo():
    tool = BashTool()
    assert tool.is_destructive is True
    
    result = await tool.execute(command="echo 'test_output'")
    assert not result.is_error
    assert "test_output" in result.output
    
@pytest.mark.asyncio
async def test_bash_timeout():
    tool = BashTool()
    result = await tool.execute(command="sleep 2", timeout=1)
    assert result.is_error
    assert "timed out" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_bash_tool.py -v`
Expected: FAIL (missing `BashTool`)

**Step 3: Write minimal implementation**

```python
# Create src/cascade/tools/bash_tool.py
import asyncio
import os
from cascade.tools.base import BaseTool, ToolResult

class BashTool(BaseTool):
    name = "bash"
    description = "Execute a shell command and return output"

    @property
    def is_destructive(self) -> bool: return True

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
            return ToolResult(output=output, is_error=proc.returncode != 0, metadata={"exit_code": proc.returncode})
        except asyncio.TimeoutError:
            return ToolResult(output=f"Command timed out after {timeout}s", is_error=True)
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_bash_tool.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/tools/bash_tool.py tests/test_bash_tool.py
git commit -m "feat(tools): implement robust BashTool with timeouts"
```

---

*(Note: We will follow this exact TDD rhythm for `FileReadTool`, `FileWriteTool`, `FileEditTool`, `GrepTool`, and `GlobTool` consecutively out of the remaining tools directory, generating one spec document per step when executed in superpowers:executing-plans).*
