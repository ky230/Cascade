import pytest
from unittest.mock import AsyncMock, patch
from cascade.engine.query import QueryEngine, QueryEngineConfig
from cascade.services.api_client import ModelClient, StreamResult

@pytest.mark.asyncio
async def test_query_engine_basic_loop():
    client = ModelClient("openai", "gpt-4o")
    
    # Mock stream to yield a string
    async def mock_stream_full(messages, tools=None, on_token=None):
        if on_token:
            on_token("Hello ")
            on_token("World!")
        return StreamResult(text="Hello World!", tool_calls=[], finish_reason="stop")
        
    client.stream_full = mock_stream_full
    engine = QueryEngine(client)
    
    tokens = []
    def on_token(t):
        tokens.append(t)
        
    result = await engine.submit("Hi", on_token=on_token)
    
    assert "".join(tokens) == "Hello World!"
    assert result.output == "Hello World!"
    assert result.stop_reason == "end_turn"
    
    # Verify transcript recorded
    assert len(engine.messages) == 2
    assert engine.messages[0]["role"] == "user"
    assert engine.messages[1]["role"] == "assistant"
    assert engine.messages[1]["content"] == "Hello World!"

@pytest.mark.asyncio
async def test_query_engine_system_prompt():
    client = ModelClient("openai", "gpt-4o")
    
    async def mock_stream_full(messages, tools=None, on_token=None):
        if on_token:
            on_token("ok")
        return StreamResult(text="ok", tool_calls=[], finish_reason="stop")
        
    client.stream_full = mock_stream_full
    engine = QueryEngine(client)
    engine.set_system_prompt("You are a test bot.")
    
    await engine.submit("hi")
    
    assert engine.messages[0]["role"] == "system"
    assert "test bot" in engine.messages[0]["content"]

@pytest.mark.asyncio
async def test_query_engine_multi_turn():
    client = ModelClient("openai", "gpt-4o")
    call_count = 0
    
    async def mock_stream_full(messages, tools=None, on_token=None):
        nonlocal call_count
        call_count += 1
        resp = f"Reply {call_count}"
        if on_token:
            on_token(resp)
        return StreamResult(text=resp, tool_calls=[], finish_reason="stop")
        
    client.stream_full = mock_stream_full
    engine = QueryEngine(client)
    
    r1 = await engine.submit("First")
    r2 = await engine.submit("Second")
    
    assert r1.output == "Reply 1"
    assert r2.output == "Reply 2"
    # Should have 4 messages: user1, assistant1, user2, assistant2
    assert len(engine.messages) == 4

@pytest.mark.asyncio
async def test_query_engine_tool_call_loop():
    """Engine should detect tool_calls, execute via registry, and loop."""
    from cascade.services.api_client import StreamResult
    from cascade.tools.base import BaseTool, ToolResult
    from cascade.tools.registry import ToolRegistry

    client = ModelClient("openai", "gpt-4o")
    registry = ToolRegistry()

    # Create a mock tool
    class MockTool(BaseTool):
        @property
        def name(self): return "mock_tool"
        @property
        def description(self): return "a mock"
        @property
        def is_read_only(self): return True
        async def execute(self, **kwargs): return ToolResult(output="tool_output_42")
        def get_input_schema(self): return {"type": "object", "properties": {"x": {"type": "string"}}}

    registry.register(MockTool())

    call_count = 0

    async def mock_stream_full(messages, tools=None, on_token=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: model wants to use a tool
            return StreamResult(
                text="",
                tool_calls=[{"id": "call_1", "name": "mock_tool", "arguments": {"x": "hello"}}],
                finish_reason="tool_calls",
            )
        else:
            # Second call: model gives final answer
            if on_token:
                on_token("Final answer")
            return StreamResult(
                text="Final answer",
                tool_calls=[],
                finish_reason="stop",
            )

    client.stream_full = mock_stream_full

    engine = QueryEngine(client, QueryEngineConfig(), registry=registry)

    tokens = []
    result = await engine.submit("do something", on_token=lambda t: tokens.append(t))

    assert result.output == "Final answer"
    assert len(result.tool_uses) == 1
    assert result.tool_uses[0]["name"] == "mock_tool"
    assert result.tool_uses[0]["result"] == "tool_output_42"
    assert call_count == 2


@pytest.mark.asyncio
async def test_query_engine_no_tools_still_works():
    """Engine without registry should work like before (text-only)."""
    from cascade.services.api_client import StreamResult

    client = ModelClient("openai", "gpt-4o")

    async def mock_stream_full(messages, tools=None, on_token=None):
        if on_token:
            on_token("Hello ")
            on_token("World!")
        return StreamResult(text="Hello World!", tool_calls=[], finish_reason="stop")

    client.stream_full = mock_stream_full

    engine = QueryEngine(client, QueryEngineConfig())

    tokens = []
    result = await engine.submit("Hi", on_token=lambda t: tokens.append(t))

    assert result.output == "Hello World!"
    assert result.tool_uses == []
    assert "".join(tokens) == "Hello World!"
