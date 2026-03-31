# Cascade LLM API Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a live, asynchronous Universal LLM Client using the OpenAI SDK format to support DeepSeek, GLM, Kimi, and other modern models by dynamically routing `base_url` and `api_key`. Fix the missing `pyproject.toml` for valid `-e .` installation.

**Architecture:** Use `python-dotenv` to securely load API keys from `.env`. Extend the existing `ModelClient` stub into an asynchronous `UniversalModelClient` wrapping `openai.AsyncOpenAI`. A provider mapping dict will route the correct base URLs.

**Tech Stack:** Python 3, `pytest`, `asyncio`, `openai` (Async), `python-dotenv`.

---

### Task 1: Package Configuration & Dependency Addition

**Files:**
- Create/Modify: `pyproject.toml`
- Create/Modify: `requirements-dev.txt`

**Step 1: Write setup/dependencies (No literal test needed for TOML)**
We will verify this step by testing the `pip install -e` itself.

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
    "openai>=1.0.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0"
]
```

```text
# Append to requirements-dev.txt
pytest-mock
```

**Step 2: Run verification**
Run: `pip install -e . && pip install -r requirements-dev.txt`
Expected: PASS (Successfully installs code as an editable package).

**Step 3: Commit**
```bash
git add pyproject.toml requirements-dev.txt
git commit -m "chore: add pyproject.toml and LLM dependencies"
```

---

### Task 2: Provider Configuration Router

**Files:**
- Create: `src/cascade/api/config.py`
- Create: `tests/api/test_config.py`

**Step 1: Write the failing test**

```python
# tests/api/test_config.py
import os
from cascade.api.config import get_provider_config

def test_get_provider_config(monkeypatch):
    monkeypatch.setenv("GLM_API_KEY", "test-key-123")
    
    config = get_provider_config("glm")
    assert config["base_url"] == "https://open.bigmodel.cn/api/paas/v4/"
    assert config["api_key"] == "test-key-123"

def test_get_unknown_provider():
    import pytest
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider_config("unknown")
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/api/test_config.py -v`
Expected: FAIL (ModuleNotFoundError for `cascade.api.config`).

**Step 3: Write minimal implementation**

```python
# src/cascade/api/config.py
import os
from dotenv import load_dotenv

load_dotenv()

PROVIDERS = {
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "env_key": "GLM_API_KEY"
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY"
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "env_key": "MOONSHOT_API_KEY"
    }
}

def get_provider_config(provider_name: str) -> dict:
    if provider_name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider_name}")
        
    cfg = PROVIDERS[provider_name]
    api_key = os.getenv(cfg["env_key"])
    
    if not api_key:
         # Optionally handle missing key, for now just allow None/empty to let client fail
         pass
         
    return {
        "base_url": cfg["base_url"],
        "api_key": api_key
    }
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/api/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/api/config.py tests/api/test_config.py
git commit -m "feat: implement LLM provider routing configuration"
```

---

### Task 3: Universal Async Model Client

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
async def test_client_init(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-ds-key")
    client = ModelClient(provider="deepseek", model_name="deepseek-chat")
    assert client.client.base_url == "https://api.deepseek.com/v1/"
    assert client.client.api_key == "test-ds-key"

@pytest.mark.asyncio
async def test_client_generate(monkeypatch, mocker):
    monkeypatch.setenv("GLM_API_KEY", "fake-key")
    client = ModelClient(provider="glm", model_name="glm-4")
    
    # Mock the AsyncOpenAI chat completions create method
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Mocked LLM reply"
    
    mock_create = AsyncMock(return_value=mock_response)
    mocker.patch.object(client.client.chat.completions, 'create', new=mock_create)
    
    result = await client.generate("Hello physics")
    
    assert result == "Mocked LLM reply"
    mock_create.assert_called_once()
    kwargs = mock_create.call_args.kwargs
    assert kwargs['model'] == "glm-4"
    assert kwargs['messages'][0]['content'] == "Hello physics"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/api/test_client.py -v`
Expected: FAIL (No attribute `client.client` or missing `provider` argument to init).

**Step 3: Write minimal implementation**

```python
# src/cascade/api/client.py
from openai import AsyncOpenAI
from cascade.api.config import get_provider_config

class ModelClient:
    """Universal interface layer for LLM routing using OpenAI SDK format."""
    
    def __init__(self, provider: str, model_name: str):
        self.provider = provider
        self.model_name = model_name
        
        config = get_provider_config(provider)
        self.client = AsyncOpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"] or "dummy" # fallback to prevent init crash if key missing
        )

    async def generate(self, prompt: str) -> str:
        """Call universal LLM endpoint to generate a text response."""
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/api/test_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/api/client.py tests/api/test_client.py
git commit -m "feat: implement AsyncOpenAI-based universal ModelClient"
```
