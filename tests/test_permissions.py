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
async def test_permission_auto_allows_safe():
    engine = PermissionEngine(mode=PermissionMode.AUTO)
    res = await engine.check(SafeTool(), {})
    assert res.allowed is True

@pytest.mark.asyncio
async def test_permission_auto_blocks_destructive():
    engine = PermissionEngine(mode=PermissionMode.AUTO)
    async def mock_ask(msg): return False
    res = await engine.check(DestructiveTool(), {}, ask_user=mock_ask)
    assert res.allowed is False

@pytest.mark.asyncio
async def test_permission_auto_approves_destructive():
    engine = PermissionEngine(mode=PermissionMode.AUTO)
    async def mock_ask(msg): return True
    res = await engine.check(DestructiveTool(), {}, ask_user=mock_ask)
    assert res.allowed is True

@pytest.mark.asyncio
async def test_permission_bypass_mode():
    engine = PermissionEngine(mode=PermissionMode.BYPASS)
    res = await engine.check(DestructiveTool(), {})
    assert res.allowed is True

@pytest.mark.asyncio
async def test_permission_default_mode_no_prompt():
    engine = PermissionEngine(mode=PermissionMode.DEFAULT)
    res = await engine.check(SafeTool(), {})
    assert res.allowed is False  # no ask_user provided → deny
