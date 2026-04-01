"""End-to-end integration test: user asks to read a file, engine loops."""
import pytest
import tempfile
import os
from cascade.services.api_client import ModelClient, StreamResult
from cascade.engine.query import QueryEngine, QueryEngineConfig
from cascade.tools.registry import ToolRegistry
from cascade.tools.file_tools import FileReadTool
from cascade.permissions.engine import PermissionEngine, PermissionMode


@pytest.mark.asyncio
async def test_e2e_file_read_tool_loop():
    """Simulate: user asks 'read /tmp/test.txt', model calls FileReadTool, 
    gets result, responds with content."""
    # Create a real temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello from the real filesystem!")
        tmp_path = f.name

    try:
        client = ModelClient("openai", "gpt-4o")
        registry = ToolRegistry()
        registry.register(FileReadTool())
        permissions = PermissionEngine(mode=PermissionMode.AUTO)

        call_count = 0

        async def mock_stream_full(messages, tools=None, on_token=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return StreamResult(
                    text="",
                    tool_calls=[{
                        "id": "call_read",
                        "name": "file_read",
                        "arguments": {"path": tmp_path},
                    }],
                    finish_reason="tool_calls",
                )
            else:
                answer = f"The file contains: {messages[-1]['content']}"
                if on_token:
                    on_token(answer)
                return StreamResult(text=answer, tool_calls=[], finish_reason="stop")

        client.stream_full = mock_stream_full

        engine = QueryEngine(client, QueryEngineConfig(), registry=registry, permissions=permissions)
        result = await engine.submit(f"Read {tmp_path}")

        assert result.stop_reason == "end_turn"
        assert len(result.tool_uses) == 1
        assert result.tool_uses[0]["name"] == "file_read"
        assert "Hello from the real filesystem!" in result.tool_uses[0]["result"]
        assert "Hello from the real filesystem!" in result.output
    finally:
        os.unlink(tmp_path)
