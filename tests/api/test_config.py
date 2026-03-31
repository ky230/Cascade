import pytest
from cascade.api.config import get_litellm_kwargs

def test_get_litellm_kwargs(monkeypatch):
    monkeypatch.setenv("GLM_API_KEY", "test-key-123")
    kwargs = get_litellm_kwargs("glm", "glm-4")
    assert kwargs["model"] == "zhipu/glm-4"
    assert kwargs["api_key"] == "test-key-123"

def test_big_three_passthrough():
    kwargs = get_litellm_kwargs("openai", "gpt-4o")
    assert kwargs["model"] == "gpt-4o"
    assert "api_key" not in kwargs  # LiteLLM native handles it
