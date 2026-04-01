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

def test_registry_list_tools():
    reg = ToolRegistry()
    reg.register(MockTool())
    tools = reg.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "mock"

@pytest.mark.asyncio
async def test_registry_execution():
    reg = ToolRegistry()
    reg.register(MockTool())
    result = await reg.execute("mock", {"msg": "hello context"})
    assert result.output == "hello context"
    assert not result.is_error

@pytest.mark.asyncio
async def test_registry_unknown_tool():
    reg = ToolRegistry()
    result = await reg.execute("nonexistent", {})
    assert result.is_error
    assert "Unknown tool" in result.output
