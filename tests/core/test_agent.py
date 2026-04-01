import pytest
from unittest.mock import AsyncMock, MagicMock
from cascade.core.agent import Agent

@pytest.mark.asyncio
async def test_agent_memory_loop(mocker):
    # Mock litellm acompletion entirely to avoid network
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I am Cascade."
    
    mock_acompletion = AsyncMock(return_value=mock_response)
    mocker.patch('cascade.api.client.acompletion', new=mock_acompletion)
    
    agent = Agent(provider="openai", model_name="gpt-4o", system_prompt="You are a HEP Assistant.")
    
    # Check initial memory
    assert len(agent.memory) == 1
    assert agent.memory[0]["role"] == "system"
    
    # First turn
    reply1 = await agent.chat("Who are you?")
    assert reply1 == "I am Cascade."
    assert len(agent.memory) == 3  # System -> User -> Assistant
    assert agent.memory[1]["content"] == "Who are you?"
    assert agent.memory[2]["content"] == "I am Cascade."
