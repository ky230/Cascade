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
