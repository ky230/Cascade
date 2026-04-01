import os
import pytest
from cascade.tools.file_tools import FileReadTool, FileWriteTool
from cascade.tools.search_tools import GrepTool, GlobTool

# ── FileReadTool ──

@pytest.mark.asyncio
async def test_file_read(tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("line1\nline2\nline3\n")
    
    tool = FileReadTool()
    assert tool.is_read_only is True
    
    result = await tool.execute(path=str(test_file))
    assert not result.is_error
    assert "line1" in result.output
    assert result.metadata["total_lines"] == 3

@pytest.mark.asyncio
async def test_file_read_range(tmp_path):
    test_file = tmp_path / "data.txt"
    test_file.write_text("a\nb\nc\nd\ne\n")
    
    tool = FileReadTool()
    result = await tool.execute(path=str(test_file), start_line=2, end_line=4)
    assert result.output == "b\nc\nd\n"

@pytest.mark.asyncio
async def test_file_read_missing():
    tool = FileReadTool()
    result = await tool.execute(path="/nonexistent/file.txt")
    assert result.is_error

# ── FileWriteTool ──

@pytest.mark.asyncio
async def test_file_write(tmp_path):
    out_file = tmp_path / "output.txt"
    
    tool = FileWriteTool()
    assert tool.is_destructive is True
    
    result = await tool.execute(path=str(out_file), content="hello world")
    assert not result.is_error
    assert out_file.read_text() == "hello world"

# ── GrepTool ──

@pytest.mark.asyncio
async def test_grep(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("def hello():\n    return 42\n")
    
    tool = GrepTool()
    result = await tool.execute(pattern="hello", path=str(tmp_path))
    assert not result.is_error
    assert "hello" in result.output

# ── GlobTool ──

@pytest.mark.asyncio
async def test_glob(tmp_path):
    (tmp_path / "a.py").touch()
    (tmp_path / "b.py").touch()
    (tmp_path / "c.txt").touch()
    
    tool = GlobTool()
    result = await tool.execute(pattern=str(tmp_path / "*.py"))
    assert not result.is_error
    assert "a.py" in result.output
    assert "b.py" in result.output
    assert "c.txt" not in result.output
