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
