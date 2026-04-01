import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from cascade.services.api_client import ModelClient

@pytest.mark.asyncio
async def test_api_client_stream():
    client = ModelClient("openai", "gpt-4o")
    
    # Mock litellm async generator chunk
    class MockDelta:
        def __init__(self, c): self.content = c
    class MockChoice:
        def __init__(self, c): self.delta = MockDelta(c)
    class MockChunk:
        def __init__(self, c): self.choices = [MockChoice(c)]
        
    async def mock_generator():
        for ch in ["A", " ", "test"]:
            yield MockChunk(ch)
            
    with patch("cascade.services.api_client.acompletion", return_value=mock_generator()):
        chunks = []
        async for c in client.stream([{"role": "user", "content": "hi"}]):
            chunks.append(c)
            
        assert chunks == ["A", " ", "test"]

@pytest.mark.asyncio
async def test_stream_passes_tools_kwarg():
    """Verify that tools schemas are forwarded to litellm.acompletion."""
    from unittest.mock import AsyncMock, patch, MagicMock

    client = ModelClient("gemini", "gemini-2.5-flash")
    tools = [{"type": "function", "function": {"name": "bash", "description": "run shell", "parameters": {}}}]

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta = MagicMock()
    mock_chunk.choices[0].delta.content = "hello"
    mock_chunk.choices[0].delta.tool_calls = None

    async def mock_acompletion(**kwargs):
        assert "tools" in kwargs
        assert kwargs["tools"] == tools
        async def gen():
            yield mock_chunk
        return gen()

    with patch("cascade.services.api_client.acompletion", side_effect=mock_acompletion):
        tokens = []
        async for token in client.stream([{"role": "user", "content": "hi"}], tools=tools):
            tokens.append(token)
        assert tokens == ["hello"]


@pytest.mark.asyncio
async def test_stream_without_tools_still_works():
    """Backward compat: stream() with no tools arg works as before."""
    from unittest.mock import AsyncMock, patch, MagicMock

    client = ModelClient("gemini", "gemini-2.5-flash")

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta = MagicMock()
    mock_chunk.choices[0].delta.content = "world"
    mock_chunk.choices[0].delta.tool_calls = None

    async def mock_acompletion(**kwargs):
        assert "tools" not in kwargs
        async def gen():
            yield mock_chunk
        return gen()

    with patch("cascade.services.api_client.acompletion", side_effect=mock_acompletion):
        tokens = []
        async for token in client.stream([{"role": "user", "content": "hi"}]):
            tokens.append(token)
        assert tokens == ["world"]


@pytest.mark.asyncio
async def test_stream_full_captures_tool_calls():
    """stream_full() should return both accumulated text and tool_calls."""
    from unittest.mock import MagicMock, patch
    from cascade.services.api_client import StreamResult

    client = ModelClient("gemini", "gemini-2.5-flash")

    # Simulate 3 chunks: text, tool_call start, tool_call args
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "Let me check "
    chunk1.choices[0].delta.tool_calls = None
    chunk1.choices[0].finish_reason = None

    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = None
    tc = MagicMock()
    tc.index = 0
    tc.id = "call_123"
    tc.function.name = "bash"
    tc.function.arguments = '{"comma'
    chunk2.choices[0].delta.tool_calls = [tc]
    chunk2.choices[0].finish_reason = None

    chunk3 = MagicMock()
    chunk3.choices = [MagicMock()]
    chunk3.choices[0].delta.content = None
    tc2 = MagicMock()
    tc2.index = 0
    tc2.id = None
    tc2.function.name = None
    tc2.function.arguments = 'nd": "ls"}'
    chunk3.choices[0].delta.tool_calls = [tc2]
    chunk3.choices[0].finish_reason = "tool_calls"

    async def mock_acompletion(**kwargs):
        async def gen():
            yield chunk1
            yield chunk2
            yield chunk3
        return gen()

    with patch("cascade.services.api_client.acompletion", side_effect=mock_acompletion):
        result = await client.stream_full(
            [{"role": "user", "content": "list files"}],
            tools=[{"type": "function", "function": {"name": "bash"}}],
            on_token=None,
        )

    assert isinstance(result, StreamResult)
    assert result.text == "Let me check "
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "bash"
    assert result.tool_calls[0]["arguments"] == {"command": "ls"}
    assert result.tool_calls[0]["id"] == "call_123"
