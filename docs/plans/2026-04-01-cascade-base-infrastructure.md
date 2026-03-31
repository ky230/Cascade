# Cascade Base Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Scaffold the base Python package for Cascade and implement the core `Tool` and `Engine` abstractions.

**Architecture:** We will create a clean Python structure using `pytest` for TDD. The core will involve an abstract `BaseTool` class (Tool Wrapper pattern) and a `QueryEngine` stub that processes inputs.

**Tech Stack:** Python 3, `pytest`, `asyncio`.

---

### Task 1: Project Scaffolding & Pytest Setup

**Files:**
- Create: `pytest.ini`
- Create: `src/cascade/__init__.py`
- Create: `tests/__init__.py`
- Test: `tests/test_sanity.py`

**Step 1: Write the failing test**

```python
# tests/test_sanity.py
def test_import_cascade():
    import cascade
    assert cascade.__name__ == "cascade"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sanity.py -v`
Expected: FAIL with "No module named 'cascade'" (if PYTHONPATH is not set)

**Step 3: Write minimal implementation**

```python
# src/cascade/__init__.py
"""Cascade: HEP Workflow Orchestrator"""
__version__ = "0.1.0"
```

```ini
# pytest.ini
[pytest]
pythonpath = src
testpaths = tests
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sanity.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pytest.ini src/ tests/
git commit -m "chore: scaffold project structure and configure pytest"
```

---

### Task 2: Base Tool Abstraction

**Files:**
- Create: `src/cascade/core/tool.py`
- Test: `tests/core/test_tool.py`

**Step 1: Write the failing test**

```python
# tests/core/test_tool.py
import pytest
import asyncio
from cascade.core.tool import BaseTool

class DummyTool(BaseTool):
    name = "dummy"
    description = "A dummy tool"
    
    async def execute(self, **kwargs):
        return f"Executed with {kwargs}"

@pytest.mark.asyncio
async def test_tool_execution():
    tool = DummyTool()
    result = await tool.execute(param="test")
    assert result == "Executed with {'param': 'test'}"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_tool.py -v`
Expected: FAIL with ModuleNotFoundError or ImportError for `cascade.core.tool`.

**Step 3: Write minimal implementation**

```python
# src/cascade/core/tool.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """Abstract base class for all Cascade tools (Tool Wrapper Pattern)."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments."""
        pass
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_tool.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/core/ tests/core/
git commit -m "feat: implement BaseTool abstract class"
```

---

### Task 3: Setup LLM Client Interface Stub

**Files:**
- Create: `src/cascade/api/client.py`
- Test: `tests/api/test_client.py`

**Step 1: Write the failing test**

```python
# tests/api/test_client.py
import pytest
from cascade.api.client import ModelClient

@pytest.mark.asyncio
async def test_client_stub():
    client = ModelClient(model_name="glm-5.1")
    assert client.model_name == "glm-5.1"
    
    # Stub response
    response = await client.generate("Hello")
    assert response == "Stub response for: Hello"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_client.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/cascade/api/client.py
class ModelClient:
    """Abstract interface layer for LLM routing."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name

    async def generate(self, prompt: str) -> str:
        """Generate response (stub implementation)."""
        return f"Stub response for: {prompt}"
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/api/test_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/api/ tests/api/
git commit -m "feat: add ModelClient stub interface"
```
