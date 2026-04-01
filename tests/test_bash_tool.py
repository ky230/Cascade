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

@pytest.mark.asyncio
async def test_bash_exit_code():
    tool = BashTool()
    result = await tool.execute(command="exit 1")
    assert result.is_error
    assert result.metadata["exit_code"] == 1

@pytest.mark.asyncio
async def test_bash_schema():
    tool = BashTool()
    schema = tool.get_input_schema()
    assert "command" in schema["properties"]
    assert schema["required"] == ["command"]
