# Phase 2: Reactive State & API Streaming Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish the foundational data flow mechanisms: A central reactive state store for UI/Engine communication, and an async streaming LLM client.
**Architecture:** Data passes immutably through `AppState`. `Store` notifies listeners of changes. `ModelClient` uses LiteLLM's `stream=True` to yield tokens lazily to the Query Engine.
**Tech Stack:** `dataclasses`, LiteLLM.

---

### Task 2.1: Immutable AppState and Reactive Store

**Files:**
- Create: `src/cascade/state/app_state.py`
- Create: `src/cascade/state/store.py`
- Create: `tests/test_state.py`

**Step 1: Write the failing test**

```python
# Create tests/test_state.py
from cascade.state.store import Store
from cascade.state.app_state import AppState

def test_store_get_set():
    store = Store()
    state = store.get_state()
    assert isinstance(state, AppState)

def test_store_subscribe():
    store = Store()
    changes = []
    store.subscribe(lambda s: changes.append(s))
    
    # Update state immutably
    store.set_state(lambda prev: prev.with_update(is_loading=True))
    
    assert len(changes) == 1
    assert changes[0].is_loading is True

def test_store_unsubscribe():
    store = Store()
    changes = []
    unsub = store.subscribe(lambda s: changes.append(s))
    unsub()
    
    store.set_state(lambda prev: prev.with_update(is_loading=True))
    assert len(changes) == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`
Expected: FAIL due to missing `cascade.state.store` module.

**Step 3: Write minimal implementation**

```python
# src/cascade/state/app_state.py
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class AppState:
    """Immutable application state."""
    is_loading: bool = False
    messages: tuple = ()
    provider: str = ""
    model: str = ""
    permission_mode: str = "default"
    verbose: bool = False
    conversation_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

    def with_update(self, **kwargs) -> AppState:
        current = asdict(self)
        current.update(kwargs)
        return AppState(**current)
```

```python
# src/cascade/state/store.py
from __future__ import annotations
from typing import Callable, List
from cascade.state.app_state import AppState

class Store:
    """Minimal reactive state store."""

    def __init__(self):
        self._state = AppState()
        self._listeners: List[Callable[[AppState], None]] = []

    def get_state(self) -> AppState:
        return self._state

    def set_state(self, updater: Callable[[AppState], AppState]) -> None:
        self._state = updater(self._state)
        for listener in self._listeners:
            listener(self._state)

    def subscribe(self, listener: Callable[[AppState], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_state.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/state tests/test_state.py
git commit -m "feat(state): implement immutable AppState and reactive Store"
```

---

### Task 2.2: API Streaming Support

**Files:**
- Modify: `src/cascade/services/api_client.py`
- Modify: `tests/test_api_client.py`

**Step 1: Write the failing test**

*(We will mock the LiteLLM response to avoid live API calls during unit tests)*

```python
# Create tests/test_api_client.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_client.py -v`
Expected: FAIL because `stream` is not defined on `ModelClient`.

**Step 3: Write minimal implementation**

```python
# src/cascade/services/api_client.py
from litellm import acompletion
from cascade.services.api_config import get_litellm_kwargs
from typing import List, Dict, AsyncIterator

class ModelClient:
    def __init__(self, provider: str, model_name: str):
        self.provider = provider
        self.model_name = model_name

    async def generate(self, messages: List[Dict[str, str]]) -> str:
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        response = await acompletion(messages=messages, **kwargs)
        return response.choices[0].message.content

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Stream tokens as they arrive."""
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        kwargs["stream"] = True
        response = await acompletion(messages=messages, **kwargs)
        async for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/services tests/test_api_client.py
git commit -m "feat(api): add async stream extraction to ModelClient"
```
