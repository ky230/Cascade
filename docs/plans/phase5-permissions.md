# Phase 5: Permission & Security Engine Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish secure execution boundaries for HPC environments by intercepting dangerous tool executions (e.g. destructive Bash commands).
**Architecture:** `PermissionEngine` intercepts tool execution attempts before they reach `BaseTool.execute()`. Operates in 3 modes: `DEFAULT` (always ask), `AUTO` (ask only for destructive actions), `BYPASS` (never ask).
**Tech Stack:** `enum`, `typing.Callable`.

---

### Task 5.1: Implement Permission Engine

**Files:**
- Create: `src/cascade/permissions/engine.py`
- Create: `tests/test_permissions.py`

**Step 1: Write the failing test**

```python
# Create tests/test_permissions.py
import pytest
from cascade.permissions.engine import PermissionEngine, PermissionMode
from cascade.tools.base import BaseTool, ToolResult

class DestructiveTool(BaseTool):
    name = "destroy"
    description = "Mock destructive tool"
    @property
    def is_destructive(self) -> bool: return True
    def get_input_schema(self): return {}
    async def execute(self, **kw): return ToolResult(output="done")

class SafeTool(BaseTool):
    name = "view"
    description = "Mock safe tool"
    @property
    def is_read_only(self) -> bool: return True
    def get_input_schema(self): return {}
    async def execute(self, **kw): return ToolResult(output="done")

@pytest.mark.asyncio
async def test_permission_auto_mode():
    engine = PermissionEngine(mode=PermissionMode.AUTO)
    
    # Safe tool is allowed automatically
    res = await engine.check(SafeTool(), {})
    assert res.allowed is True
    
    # Destructive tool needs asking
    async def mock_ask(msg): return False
    res2 = await engine.check(DestructiveTool(), {}, ask_user=mock_ask)
    assert res2.allowed is False

@pytest.mark.asyncio
async def test_permission_bypass_mode():
    engine = PermissionEngine(mode=PermissionMode.BYPASS)
    res = await engine.check(DestructiveTool(), {})
    assert res.allowed is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_permissions.py -v`
Expected: FAIL (missing module)

**Step 3: Write minimal implementation**

```python
# Create src/cascade/permissions/engine.py
from __future__ import annotations
from enum import Enum
from typing import Optional, Callable, Awaitable
from cascade.tools.base import BaseTool

class PermissionMode(str, Enum):
    DEFAULT = "default"    # Always ask if ask_user is provided
    AUTO = "auto"          # Auto-allow if read_only, ask otherwise
    BYPASS = "bypass"      # Danger: Allow everything

class PermissionResult:
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason

class PermissionEngine:
    def __init__(self, mode: PermissionMode = PermissionMode.DEFAULT):
        self.mode = mode
        self._always_allow: set[str] = set()
        self._always_deny: set[str] = set()

    async def check(
        self,
        tool: BaseTool,
        input: dict,
        ask_user: Optional[Callable[[str], Awaitable[bool]]] = None,
    ) -> PermissionResult:
        
        if tool.name in self._always_deny:
            return PermissionResult(False, "denied by rule")
            
        if tool.name in self._always_allow:
            return PermissionResult(True, "allowed by rule")
            
        if self.mode == PermissionMode.BYPASS:
            return PermissionResult(True, "bypass mode")
            
        if self.mode == PermissionMode.AUTO and tool.is_read_only:
            return PermissionResult(True, "auto-allowed safe tool")
            
        if ask_user:
            allowed = await ask_user(f"Allow {tool.user_facing_name(input)}? [y/N]")
            return PermissionResult(allowed, "user interactive decision")
            
        return PermissionResult(False, "no interactive prompt available")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_permissions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/permissions/engine.py tests/test_permissions.py
git commit -m "feat(permissions): implement mode-based PermissionEngine (Auto/Ask/Bypass)"
```
