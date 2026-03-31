import pytest
from unittest.mock import AsyncMock, MagicMock
from cascade.api.client import ModelClient

@pytest.mark.asyncio
async def test_client_generate(mocker):
    client = ModelClient(provider="openai", model_name="gpt-4o")
    
    # Mock litellm.acompletion
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Mocked LLM reply"
    
    mock_acompletion = AsyncMock(return_value=mock_response)
    mocker.patch('cascade.api.client.acompletion', new=mock_acompletion)
    
    result = await client.generate("Hello physics")
    
    assert result == "Mocked LLM reply"
    mock_acompletion.assert_called_once()
    kwargs = mock_acompletion.call_args.kwargs
    assert kwargs['model'] == "gpt-4o"
    assert kwargs['messages'][0]['content'] == "Hello physics"
