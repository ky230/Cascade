# Cascade LLM API Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a universal, asynchronous LLM Client that supports both the "Big Three" (OpenAI, Anthropic, Gemini) and local/Chinese models (GLM, DeepSeek, Kimi). Fix the missing `pyproject.toml` for valid `-e .` installation.

**Architecture:** We will use `litellm`, the industry standard for routing multi-model calls via a unified Async OpenAI-like interface. `litellm.acompletion` perfectly handles all native and proxy base URLs.

**Tech Stack:** Python 3, `pytest`, `asyncio`, `litellm`, `python-dotenv`.

---

### Task 1: Package Configuration & Dependency Addition

**Files:**
- Create/Modify: `pyproject.toml`
- Create/Modify: `requirements-dev.txt`

**Step 1: Write setup/dependencies**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "cascade"
version = "0.1.0"
description = "HEP Workflow Orchestrator"
dependencies = [
    "litellm>=1.0.0",
    "python-dotenv>=1.0.0"
]
```

```text
# Append to requirements-dev.txt
pytest-mock
```

**Step 2: Run verification**
Run: `pip install -e . && pip install -r requirements-dev.txt`
Expected: PASS

**Step 3: Commit**
```bash
git add pyproject.toml requirements-dev.txt
git commit -m "chore: add pyproject.toml and litellm dependencies"
```

---

### Task 2: Provider Configuration Mapping

**Files:**
- Create: `src/cascade/api/config.py`
- Create: `tests/api/test_config.py`

**Step 1: Write the failing test**

```python
# tests/api/test_config.py
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
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/api/test_config.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/cascade/api/config.py
import os
from dotenv import load_dotenv

load_dotenv()

CUSTOM_PROVIDERS = {
    "glm": {
        "prefix": "zhipu/",
        "env_key": "GLM_API_KEY",
        "base_url": None
    },
    "deepseek": {
        "prefix": "deepseek/",
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": None
    },
    "kimi": {
        "prefix": "moonshot/",
        "env_key": "MOONSHOT_API_KEY",
        "base_url": None
    }
}

def get_litellm_kwargs(provider_name: str, model_name: str) -> dict:
    """Resolve LiteLLM kwargs depending on whether it's native or custom."""
    if provider_name in CUSTOM_PROVIDERS:
        cfg = CUSTOM_PROVIDERS[provider_name]
        kwargs = {"model": f"{cfg['prefix']}{model_name}"}
        
        # Explicitly pass api key for custom ones
        api_key = os.getenv(cfg["env_key"])
        if api_key:
            kwargs["api_key"] = api_key
        return kwargs
    
    # For OpenAI/Anthropic/Gemini, litellm natively identifies the model and grabs os.environ
    return {"model": model_name}
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/api/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/api/config.py tests/api/test_config.py
git commit -m "feat: implement litellm unified provider mapping"
```

---

### Task 3: Universal Litellm Async Client

**Files:**
- Replace Stub in: `src/cascade/api/client.py`
- Modify: `tests/api/test_client.py`

**Step 1: Write the failing test**

```python
# tests/api/test_client.py
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
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/api/test_client.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/cascade/api/client.py
from litellm import acompletion
from cascade.api.config import get_litellm_kwargs

class ModelClient:
    """Universal interface layer for all LLMs using LiteLLM."""
    
    def __init__(self, provider: str, model_name: str):
        self.provider = provider
        self.model_name = model_name

    async def generate(self, prompt: str) -> str:
        """Call universal LLM endpoint asynchronously."""
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        
        response = await acompletion(
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/api/test_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/api/client.py tests/api/test_client.py
git commit -m "feat: implement Universal ModelClient wrapping litellm"
```
