# Phase 7: Tool Execution Loop — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the LLM's tool call decisions to real tool execution, creating a fully autonomous agent loop that can read files, run commands, and write code without human intervention.

**Architecture:** Upgrade `ModelClient` to pass tool schemas via LiteLLM's OpenAI-compatible `tools` parameter. Refactor `QueryEngine.submit()` to detect `tool_calls` in streamed responses, dispatch them through `ToolRegistry.execute()`, check permissions via `PermissionEngine`, feed results back as `tool` role messages, and loop until the model emits a final text response (or hits `max_tool_rounds`). Update `CascadeRepl` to render tool invocations and results in real-time.

**Tech Stack:** Python 3.11+, LiteLLM (OpenAI-compatible tool_calls protocol), pytest + pytest-asyncio, rich (UI rendering)

---

## Task 1: Upgrade ModelClient to Support Tool Definitions

**Files:**
- Modify: `src/cascade/services/api_client.py`
- Test: `tests/test_api_client.py`

**Step 1: Write the failing test**

Add to `tests/test_api_client.py`:

```python
@pytest.mark.asyncio
async def test_stream_passes_tools_kwarg():
    """Verify that tools schemas are forwarded to litellm.acompletion."""
    from unittest.mock import AsyncMock, patch, MagicMock

    client = ModelClient("gemini", "gemini-2.5-flash")
    tools = [{"type": "function", "function": {"name": "bash", "description": "run shell", "parameters": {}}}]

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta = MagicMock()
    mock_chunk.choices[0].delta.content = "hello"
    mock_chunk.choices[0].delta.tool_calls = None

    async def mock_acompletion(**kwargs):
        assert "tools" in kwargs
        assert kwargs["tools"] == tools
        async def gen():
            yield mock_chunk
        return gen()

    with patch("cascade.services.api_client.acompletion", side_effect=mock_acompletion):
        tokens = []
        async for token in client.stream([{"role": "user", "content": "hi"}], tools=tools):
            tokens.append(token)
        assert tokens == ["hello"]


@pytest.mark.asyncio
async def test_stream_without_tools_still_works():
    """Backward compat: stream() with no tools arg works as before."""
    from unittest.mock import AsyncMock, patch, MagicMock

    client = ModelClient("gemini", "gemini-2.5-flash")

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta = MagicMock()
    mock_chunk.choices[0].delta.content = "world"
    mock_chunk.choices[0].delta.tool_calls = None

    async def mock_acompletion(**kwargs):
        assert "tools" not in kwargs
        async def gen():
            yield mock_chunk
        return gen()

    with patch("cascade.services.api_client.acompletion", side_effect=mock_acompletion):
        tokens = []
        async for token in client.stream([{"role": "user", "content": "hi"}]):
            tokens.append(token)
        assert tokens == ["world"]
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate && pytest tests/test_api_client.py -v`
Expected: FAIL — `stream()` does not accept `tools` keyword

**Step 3: Write minimal implementation**

Replace `src/cascade/services/api_client.py` with:

```python
from litellm import acompletion
from cascade.services.api_config import get_litellm_kwargs
from typing import List, Dict, AsyncIterator, Optional

class ModelClient:
    def __init__(self, provider: str, model_name: str):
        self.provider = provider
        self.model_name = model_name

    async def generate(self, messages: List[Dict[str, str]]) -> str:
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        response = await acompletion(messages=messages, **kwargs)
        return response.choices[0].message.content

    async def stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
    ) -> AsyncIterator[str]:
        """Stream tokens. Yields text content only; tool_calls are accumulated separately."""
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        kwargs["stream"] = True
        if tools:
            kwargs["tools"] = tools
        response = await acompletion(messages=messages, **kwargs)
        async for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_client.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/cascade/services/api_client.py tests/test_api_client.py
git commit -m "feat(api): add tools parameter to ModelClient.stream()"
```

---

## Task 2: Create StreamResult to Capture Both Text and Tool Calls

**Files:**
- Modify: `src/cascade/services/api_client.py`
- Test: `tests/test_api_client.py`

**Step 1: Write the failing test**

Add to `tests/test_api_client.py`:

```python
@pytest.mark.asyncio
async def test_stream_full_captures_tool_calls():
    """stream_full() should return both accumulated text and tool_calls."""
    from unittest.mock import MagicMock, patch
    from cascade.services.api_client import StreamResult

    client = ModelClient("gemini", "gemini-2.5-flash")

    # Simulate 3 chunks: text, tool_call start, tool_call args
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "Let me check "
    chunk1.choices[0].delta.tool_calls = None
    chunk1.choices[0].finish_reason = None

    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = None
    tc = MagicMock()
    tc.index = 0
    tc.id = "call_123"
    tc.function.name = "bash"
    tc.function.arguments = '{"comma'
    chunk2.choices[0].delta.tool_calls = [tc]
    chunk2.choices[0].finish_reason = None

    chunk3 = MagicMock()
    chunk3.choices = [MagicMock()]
    chunk3.choices[0].delta.content = None
    tc2 = MagicMock()
    tc2.index = 0
    tc2.id = None
    tc2.function.name = None
    tc2.function.arguments = 'nd": "ls"}'
    chunk3.choices[0].delta.tool_calls = [tc2]
    chunk3.choices[0].finish_reason = "tool_calls"

    async def mock_acompletion(**kwargs):
        async def gen():
            yield chunk1
            yield chunk2
            yield chunk3
        return gen()

    with patch("cascade.services.api_client.acompletion", side_effect=mock_acompletion):
        result = await client.stream_full(
            [{"role": "user", "content": "list files"}],
            tools=[{"type": "function", "function": {"name": "bash"}}],
            on_token=None,
        )

    assert isinstance(result, StreamResult)
    assert result.text == "Let me check "
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "bash"
    assert result.tool_calls[0]["arguments"] == {"command": "ls"}
    assert result.tool_calls[0]["id"] == "call_123"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_client.py::test_stream_full_captures_tool_calls -v`
Expected: FAIL — `StreamResult` and `stream_full` don't exist yet

**Step 3: Write minimal implementation**

Add to `src/cascade/services/api_client.py`:

```python
import json
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class StreamResult:
    """Result of a full streaming call — text + any tool_calls."""
    text: str = ""
    tool_calls: list = field(default_factory=list)
    finish_reason: str = ""
```

Add `stream_full` method to `ModelClient`:

```python
    async def stream_full(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> "StreamResult":
        """Stream a response, accumulating both text and tool_calls.
        
        Returns a StreamResult with the full text and parsed tool calls.
        """
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        kwargs["stream"] = True
        if tools:
            kwargs["tools"] = tools
        
        response = await acompletion(messages=messages, **kwargs)
        
        text_parts = []
        tool_call_accum: dict[int, dict] = {}  # index -> {id, name, arguments_str}
        finish_reason = ""
        
        async for chunk in response:
            if not hasattr(chunk, 'choices') or len(chunk.choices) == 0:
                continue
            delta = chunk.choices[0].delta
            finish_reason = getattr(chunk.choices[0], 'finish_reason', '') or finish_reason
            
            # Accumulate text
            if hasattr(delta, 'content') and delta.content:
                text_parts.append(delta.content)
                if on_token:
                    on_token(delta.content)
            
            # Accumulate tool calls
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_call_accum:
                        tool_call_accum[idx] = {
                            "id": getattr(tc, 'id', None) or "",
                            "name": getattr(tc.function, 'name', None) or "",
                            "arguments_str": "",
                        }
                    entry = tool_call_accum[idx]
                    if getattr(tc, 'id', None):
                        entry["id"] = tc.id
                    if getattr(tc.function, 'name', None):
                        entry["name"] = tc.function.name
                    if getattr(tc.function, 'arguments', None):
                        entry["arguments_str"] += tc.function.arguments
        
        # Parse accumulated tool calls
        parsed_tool_calls = []
        for idx in sorted(tool_call_accum.keys()):
            entry = tool_call_accum[idx]
            try:
                args = json.loads(entry["arguments_str"]) if entry["arguments_str"] else {}
            except json.JSONDecodeError:
                args = {"_raw": entry["arguments_str"]}
            parsed_tool_calls.append({
                "id": entry["id"],
                "name": entry["name"],
                "arguments": args,
            })
        
        return StreamResult(
            text="".join(text_parts),
            tool_calls=parsed_tool_calls,
            finish_reason=finish_reason,
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_client.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/cascade/services/api_client.py tests/test_api_client.py
git commit -m "feat(api): add stream_full() with tool_call accumulation"
```

---

## Task 3: Refactor QueryEngine to Use stream_full and Execute Tools

**Files:**
- Modify: `src/cascade/engine/query.py`
- Modify: `tests/test_query_engine.py`

**Step 1: Write the failing test**

Add to `tests/test_query_engine.py`:

```python
@pytest.mark.asyncio
async def test_query_engine_tool_call_loop():
    """Engine should detect tool_calls, execute via registry, and loop."""
    from cascade.services.api_client import StreamResult
    from cascade.tools.base import BaseTool, ToolResult
    from cascade.tools.registry import ToolRegistry

    client = ModelClient("openai", "gpt-4o")
    registry = ToolRegistry()

    # Create a mock tool
    class MockTool(BaseTool):
        @property
        def name(self): return "mock_tool"
        @property
        def description(self): return "a mock"
        @property
        def is_read_only(self): return True
        async def execute(self, **kwargs): return ToolResult(output="tool_output_42")
        def get_input_schema(self): return {"type": "object", "properties": {"x": {"type": "string"}}}

    registry.register(MockTool())

    call_count = 0

    async def mock_stream_full(messages, tools=None, on_token=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: model wants to use a tool
            return StreamResult(
                text="",
                tool_calls=[{"id": "call_1", "name": "mock_tool", "arguments": {"x": "hello"}}],
                finish_reason="tool_calls",
            )
        else:
            # Second call: model gives final answer
            if on_token:
                on_token("Final answer")
            return StreamResult(
                text="Final answer",
                tool_calls=[],
                finish_reason="stop",
            )

    client.stream_full = mock_stream_full

    engine = QueryEngine(client, QueryEngineConfig(), registry=registry)

    tokens = []
    result = await engine.submit("do something", on_token=lambda t: tokens.append(t))

    assert result.output == "Final answer"
    assert len(result.tool_uses) == 1
    assert result.tool_uses[0]["name"] == "mock_tool"
    assert result.tool_uses[0]["result"] == "tool_output_42"
    assert call_count == 2


@pytest.mark.asyncio
async def test_query_engine_no_tools_still_works():
    """Engine without registry should work like before (text-only)."""
    from cascade.services.api_client import StreamResult

    client = ModelClient("openai", "gpt-4o")

    async def mock_stream_full(messages, tools=None, on_token=None):
        if on_token:
            on_token("Hello ")
            on_token("World!")
        return StreamResult(text="Hello World!", tool_calls=[], finish_reason="stop")

    client.stream_full = mock_stream_full

    engine = QueryEngine(client, QueryEngineConfig())

    tokens = []
    result = await engine.submit("Hi", on_token=lambda t: tokens.append(t))

    assert result.output == "Hello World!"
    assert result.tool_uses == []
    assert "".join(tokens) == "Hello World!"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_engine.py -v`
Expected: FAIL — `QueryEngine.__init__` doesn't accept `registry`, and `submit()` uses old `stream()` API

**Step 3: Write minimal implementation**

Replace `src/cascade/engine/query.py`:

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from cascade.services.api_client import ModelClient, StreamResult
from cascade.tools.registry import ToolRegistry
from cascade.tools.base import ToolResult


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
        registry: ToolRegistry | None = None,
    ):
        self.client = client
        self.config = config or QueryEngineConfig()
        self.messages: List[Dict] = []
        self.registry = registry

    def set_system_prompt(self, prompt: str) -> None:
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = {"role": "system", "content": prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    async def submit(
        self,
        user_input: str,
        on_token: Callable[[str], None] | None = None,
        on_tool_start: Callable[[str, dict], None] | None = None,
        on_tool_end: Callable[[str, ToolResult], None] | None = None,
    ) -> TurnResult:
        """Process a user message through the agentic tool loop."""
        self.messages.append({"role": "user", "content": user_input})

        tool_schemas = self.registry.get_tool_schemas() if self.registry else None
        all_tool_uses = []

        for round_idx in range(self.config.max_tool_rounds):
            # Stream the LLM response
            result: StreamResult = await self.client.stream_full(
                self.messages,
                tools=tool_schemas if tool_schemas else None,
                on_token=on_token,
            )

            # Build the assistant message for the transcript
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": result.text or ""}
            if result.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        }
                    }
                    for tc in result.tool_calls
                ]
            self.messages.append(assistant_msg)

            # If no tool calls, we're done
            if not result.tool_calls:
                return TurnResult(
                    output=result.text,
                    tool_uses=all_tool_uses,
                    stop_reason="end_turn",
                )

            # Execute each tool call
            for tc in result.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_id = tc["id"]

                if on_tool_start:
                    on_tool_start(tool_name, tool_args)

                if self.registry:
                    tool_result = await self.registry.execute(tool_name, tool_args)
                else:
                    tool_result = ToolResult(output=f"No registry for {tool_name}", is_error=True)

                if on_tool_end:
                    on_tool_end(tool_name, tool_result)

                all_tool_uses.append({
                    "name": tool_name,
                    "input": tool_args,
                    "result": tool_result.output,
                    "is_error": tool_result.is_error,
                })

                # Feed tool result back to the model
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": tool_result.output,
                })

        return TurnResult(
            output="Max tool rounds reached",
            tool_uses=all_tool_uses,
            stop_reason="max_rounds",
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_query_engine.py -v`
Expected: ALL PASS (including the 3 existing tests — they need minor updates to mock `stream_full` instead of `stream`)

> **Note:** The 3 existing tests (`test_query_engine_basic_loop`, `test_query_engine_system_prompt`, `test_query_engine_multi_turn`) must be updated to mock `client.stream_full` instead of `client.stream`. Each should return `StreamResult(text=..., tool_calls=[], finish_reason="stop")`.

**Step 5: Commit**

```bash
git add src/cascade/engine/query.py tests/test_query_engine.py
git commit -m "feat(engine): implement agentic tool execution loop in QueryEngine"
```

---

## Task 4: Wire PermissionEngine into QueryEngine

**Files:**
- Modify: `src/cascade/engine/query.py`
- Test: `tests/test_query_engine.py`

**Step 1: Write the failing test**

Add to `tests/test_query_engine.py`:

```python
@pytest.mark.asyncio
async def test_query_engine_permission_denied():
    """When PermissionEngine denies a tool, result should show permission error."""
    from cascade.services.api_client import StreamResult
    from cascade.tools.base import BaseTool, ToolResult
    from cascade.tools.registry import ToolRegistry
    from cascade.permissions.engine import PermissionEngine, PermissionMode

    client = ModelClient("openai", "gpt-4o")
    registry = ToolRegistry()

    class DangerTool(BaseTool):
        @property
        def name(self): return "danger_tool"
        @property
        def description(self): return "dangerous"
        @property
        def is_read_only(self): return False
        @property
        def is_destructive(self): return True
        async def execute(self, **kwargs): return ToolResult(output="should not reach")
        def get_input_schema(self): return {"type": "object", "properties": {}}

    registry.register(DangerTool())
    # DEFAULT mode with no ask_user → should deny non-read-only tools
    permissions = PermissionEngine(mode=PermissionMode.DEFAULT)

    call_count = 0
    async def mock_stream_full(messages, tools=None, on_token=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return StreamResult(
                text="", tool_calls=[{"id": "c1", "name": "danger_tool", "arguments": {}}],
                finish_reason="tool_calls",
            )
        else:
            if on_token:
                on_token("Permission was denied")
            return StreamResult(text="Permission was denied", tool_calls=[], finish_reason="stop")

    client.stream_full = mock_stream_full

    engine = QueryEngine(client, QueryEngineConfig(), registry=registry, permissions=permissions)
    result = await engine.submit("do danger")

    assert len(result.tool_uses) == 1
    assert result.tool_uses[0]["is_error"] is True
    assert "denied" in result.tool_uses[0]["result"].lower() or "permission" in result.tool_uses[0]["result"].lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_engine.py::test_query_engine_permission_denied -v`
Expected: FAIL — `QueryEngine.__init__()` doesn't accept `permissions`

**Step 3: Write minimal implementation**

Add `permissions` parameter to `QueryEngine.__init__`:

```python
    def __init__(
        self,
        client: ModelClient,
        config: QueryEngineConfig | None = None,
        registry: ToolRegistry | None = None,
        permissions: "PermissionEngine | None" = None,
    ):
        ...
        self.permissions = permissions
```

In the tool execution loop inside `submit()`, before calling `self.registry.execute()`:

```python
                # Permission check
                if self.permissions and self.registry:
                    tool_obj = self.registry.get(tool_name)
                    if tool_obj:
                        perm = await self.permissions.check(tool_obj, tool_args)
                        if not perm.allowed:
                            tool_result = ToolResult(
                                output=f"Permission denied: {perm.reason}",
                                is_error=True,
                            )
                            # Skip execution, feed denial back
                            if on_tool_end:
                                on_tool_end(tool_name, tool_result)
                            all_tool_uses.append({...})
                            self.messages.append({"role": "tool", ...})
                            continue
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_query_engine.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/cascade/engine/query.py tests/test_query_engine.py
git commit -m "feat(engine): wire PermissionEngine into tool execution loop"
```

---

## Task 5: Update CascadeRepl to Use New Engine API and Render Tool Calls

**Files:**
- Modify: `src/cascade/ui/app.py`
- Modify: `src/cascade/ui/renderer.py`

**Step 1: Write the failing test**

Add to `tests/test_renderer.py`:

```python
def test_render_tool_use():
    """Renderer should format tool invocations."""
    from io import StringIO
    from rich.console import Console
    from cascade.ui.renderer import MessageRenderer

    console = Console(file=StringIO(), force_terminal=True, width=80)
    renderer = MessageRenderer(console)

    # Should not raise
    renderer.render_tool_start("bash", {"command": "ls -la"})
    renderer.render_tool_end("bash", "file1.txt\nfile2.txt")

    output = console.file.getvalue()
    assert "bash" in output.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_renderer.py -v`
Expected: FAIL — `render_tool_start` / `render_tool_end` don't exist

**Step 3: Write minimal implementation**

Add to `src/cascade/ui/renderer.py`:

```python
    def render_tool_start(self, tool_name: str, tool_input: dict) -> None:
        """Show that a tool is about to execute."""
        input_preview = str(tool_input)
        if len(input_preview) > 120:
            input_preview = input_preview[:120] + "..."
        self.console.print(
            Panel(
                f"[dim]{input_preview}[/dim]",
                title=f"⚙ {tool_name}",
                title_align="left",
                border_style="yellow",
                expand=False,
            )
        )

    def render_tool_end(self, tool_name: str, output: str, is_error: bool = False) -> None:
        """Show the result of a tool execution."""
        style = "red" if is_error else "green"
        label = "✗ Error" if is_error else "✓ Result"
        display = output if len(output) <= 500 else output[:500] + "\n..."
        self.console.print(
            Panel(
                display,
                title=f"{label}: {tool_name}",
                title_align="left",
                border_style=style,
                expand=False,
            )
        )
```

Then update `src/cascade/ui/app.py` to:
1. Pass `registry` and `permissions` to `QueryEngine()`
2. Pass `on_tool_start` and `on_tool_end` callbacks to `engine.submit()`
3. Use `on_tool_start` → `self.renderer.render_tool_start(name, args)`
4. Use `on_tool_end` → `self.renderer.render_tool_end(name, result.output, result.is_error)`

Key changes in `CascadeRepl.__init__`:

```python
        self.engine = QueryEngine(
            client, QueryEngineConfig(),
            registry=self.registry,
            permissions=self.permissions,
        )
```

Key changes in the REPL loop (`run()`):

```python
                def handle_tool_start(name, args):
                    if live is not None:
                        live.stop()
                    self.renderer.render_tool_start(name, args)

                def handle_tool_end(name, tool_result):
                    self.renderer.render_tool_end(name, tool_result.output, tool_result.is_error)
                    # Restart spinner for next LLM round
                    nonlocal spinner
                    spinner = Spinner(message="Generating")
                    spinner.start()

                result = await self.engine.submit(
                    user_input,
                    on_token=on_token,
                    on_tool_start=handle_tool_start,
                    on_tool_end=handle_tool_end,
                )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/cascade/ui/app.py src/cascade/ui/renderer.py tests/test_renderer.py
git commit -m "feat(ui): render tool invocations and results in REPL"
```

---

## Task 6: End-to-End Integration Smoke Test

**Files:**
- Create: `tests/test_integration_tool_loop.py`

**Step 1: Write the integration test**

```python
"""End-to-end integration test: user asks to read a file, engine loops."""
import pytest
import tempfile
import os
from cascade.services.api_client import ModelClient, StreamResult
from cascade.engine.query import QueryEngine, QueryEngineConfig
from cascade.tools.registry import ToolRegistry
from cascade.tools.file_tools import FileReadTool
from cascade.permissions.engine import PermissionEngine, PermissionMode


@pytest.mark.asyncio
async def test_e2e_file_read_tool_loop():
    """Simulate: user asks 'read /tmp/test.txt', model calls FileReadTool, 
    gets result, responds with content."""
    # Create a real temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello from the real filesystem!")
        tmp_path = f.name

    try:
        client = ModelClient("openai", "gpt-4o")
        registry = ToolRegistry()
        registry.register(FileReadTool())
        permissions = PermissionEngine(mode=PermissionMode.AUTO)

        call_count = 0

        async def mock_stream_full(messages, tools=None, on_token=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return StreamResult(
                    text="",
                    tool_calls=[{
                        "id": "call_read",
                        "name": "file_read",
                        "arguments": {"file_path": tmp_path},
                    }],
                    finish_reason="tool_calls",
                )
            else:
                answer = f"The file contains: {messages[-1]['content']}"
                if on_token:
                    on_token(answer)
                return StreamResult(text=answer, tool_calls=[], finish_reason="stop")

        client.stream_full = mock_stream_full

        engine = QueryEngine(client, QueryEngineConfig(), registry=registry, permissions=permissions)
        result = await engine.submit(f"Read {tmp_path}")

        assert result.stop_reason == "end_turn"
        assert len(result.tool_uses) == 1
        assert result.tool_uses[0]["name"] == "file_read"
        assert "Hello from the real filesystem!" in result.tool_uses[0]["result"]
        assert "Hello from the real filesystem!" in result.output
    finally:
        os.unlink(tmp_path)
```

**Step 2: Run the test**

Run: `pytest tests/test_integration_tool_loop.py -v`
Expected: PASS

**Step 3: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS (target: ~45 tests)

**Step 4: Commit**

```bash
git add tests/test_integration_tool_loop.py
git commit -m "test: add e2e integration test for tool execution loop"
```

---

## Task 7: Manual Smoke Test with Real LLM

**No code changes — validation only.**

**Step 1: Launch Cascade**

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade
source .venv/bin/activate
cascade chat
```

**Step 2: Test tool execution**

Type: `请读取 /Users/ky230/Desktop/Private/Workspace/Git/Cascade/pyproject.toml 的内容`

Expected behavior:
1. Spinner shows "Generating..."
2. Model decides to call `file_read` tool
3. Yellow panel appears: `⚙ file_read` with the path
4. Green panel appears: `✓ Result: file_read` with file contents
5. Spinner restarts
6. Model streams a summary of the file

**Step 3: Test bash tool**

Type: `运行 echo "Cascade v0.3.0 is alive!" 这个命令`

Expected: Same flow, with `bash` tool panels instead.

**Step 4: Final commit & tag**

```bash
git tag v0.3.0
git push origin main --tags
```
