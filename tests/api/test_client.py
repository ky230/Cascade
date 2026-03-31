import pytest
from cascade.api.client import ModelClient

@pytest.mark.asyncio
async def test_client_stub():
    client = ModelClient(model_name="glm-5.1")
    assert client.model_name == "glm-5.1"
    
    # Stub response
    response = await client.generate("Hello")
    assert response == "Stub response for: Hello"
