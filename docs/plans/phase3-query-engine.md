# Phase 3: Core Query Engine Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build `QueryEngine`, the central orchestrator that manages multi-turn conversation loops, streams responses, and prepares the ground for tool execution (which will be fully implemented in Phase 4).
**Architecture:** `QueryEngine` wraps `ModelClient`. It holds its own mutable `messages` list for the session transcript.
**Tech Stack:** `asyncio`.

---

### Task 3.1: Core Query Loop

**Files:**
- Create: `src/cascade/engine/query.py`
- Create: `tests/test_query_engine.py`

**Step 1: Write the failing test**

```python
# Create tests/test_query_engine.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_engine.py -v`
Expected: FAIL due to missing `cascade.engine.query` module.

**Step 3: Write minimal implementation**

```python
# src/cascade/engine/query.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
from cascade.services.api_client import ModelClient

@dataclass
class QueryEngineConfig:
    max_turns: int = 25
    max_tool_rounds: int = 10

@dataclass
class TurnResult:
    output: str
    tool_uses: list
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0

class QueryEngine:
    """Core query engine — multi-turn tool-use loop."""

    def __init__(
        self,
        client: ModelClient,
        config: QueryEngineConfig | None = None,
    ):
        self.client = client
        self.config = config or QueryEngineConfig()
        self.messages: List[Dict[str, str]] = []

    def set_system_prompt(self, prompt: str) -> None:
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = {"role": "system", "content": prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    async def submit(
        self,
        user_input: str,
        on_token: Callable[[str], None] | None = None,
    ) -> TurnResult:
        """Process a user message through the query loop."""
        self.messages.append({"role": "user", "content": user_input})

        for round_idx in range(self.config.max_tool_rounds):
            full_response = ""
            async for token in self.client.stream(self.messages):
                full_response += token
                if on_token:
                    on_token(token)

            self.messages.append({"role": "assistant", "content": full_response})

            tool_calls = self._extract_tool_calls(full_response)
            if not tool_calls:
                return TurnResult(
                    output=full_response,
                    tool_uses=[],
                    stop_reason="end_turn",
                )

            # Placeholder for tool execution phase formatting
            for call in tool_calls:
                self.messages.append({
                    "role": "user",
                    "content": f"Tool execution not yet implemented for {call['name']}"
                })

        return TurnResult(
            output="Max tool rounds reached",
            tool_uses=[],
            stop_reason="max_rounds",
        )

    def _extract_tool_calls(self, response: str) -> list:
        """Extract tool_use blocks. Placeholder for Phase 4."""
        return []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_query_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/engine tests/test_query_engine.py
git commit -m "feat(engine): implement base QueryEngine loop and TurnResult"
```
