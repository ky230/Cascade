import pytest
import asyncio
from cascade.core.tool import BaseTool

class DummyTool(BaseTool):
    name = "dummy"
    description = "A dummy tool"
    
    async def execute(self, **kwargs):
        return f"Executed with {kwargs}"

@pytest.mark.asyncio
async def test_tool_execution():
    tool = DummyTool()
    assert tool.name == "dummy"
    assert tool.description == "A dummy tool"
    result = await tool.execute(param="test")
    assert result == "Executed with {'param': 'test'}"
