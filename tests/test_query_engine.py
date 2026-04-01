import pytest
from unittest.mock import AsyncMock, patch
from cascade.engine.query import QueryEngine, QueryEngineConfig
from cascade.services.api_client import ModelClient

@pytest.mark.asyncio
async def test_query_engine_basic_loop():
    client = ModelClient("openai", "gpt-4o")
    
    # Mock stream to yield a string
    async def mock_stream(messages):
        yield "Hello "
        yield "World!"
        
    client.stream = mock_stream
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
    
    async def mock_stream(messages):
        yield "ok"
        
    client.stream = mock_stream
    engine = QueryEngine(client)
    engine.set_system_prompt("You are a test bot.")
    
    await engine.submit("hi")
    
    assert engine.messages[0]["role"] == "system"
    assert "test bot" in engine.messages[0]["content"]

@pytest.mark.asyncio
async def test_query_engine_multi_turn():
    client = ModelClient("openai", "gpt-4o")
    call_count = 0
    
    async def mock_stream(messages):
        nonlocal call_count
        call_count += 1
        yield f"Reply {call_count}"
        
    client.stream = mock_stream
    engine = QueryEngine(client)
    
    r1 = await engine.submit("First")
    r2 = await engine.submit("Second")
    
    assert r1.output == "Reply 1"
    assert r2.output == "Reply 2"
    # Should have 4 messages: user1, assistant1, user2, assistant2
    assert len(engine.messages) == 4
