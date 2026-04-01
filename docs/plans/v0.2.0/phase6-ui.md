# Phase 6: UI Rendering Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bind the pieces together. The `CascadeRepl` running on `prompt_toolkit` will now dispatch input through the `QueryEngine`, display streaming output via `Rich.Live`, and handle interactive tool permission requests.
**Architecture:** `CascadeRepl` owns `QueryEngine`, `Store`, `PermissionEngine`, and `ToolRegistry`. `prompt_toolkit` sits on the main thread loop handling `SIGWINCH` smoothly while output is progressively written to `sys.stdout`.
**Tech Stack:** `prompt_toolkit`, `rich`, `asyncio`.

---

### Task 6.1: Build the Markdown Renderer

**Files:**
- Create: `src/cascade/ui/renderer.py`
- Test: `tests/test_renderer.py`

**Step 1: Write the failing test**

```python
# Create tests/test_renderer.py
import pytest
from unittest.mock import MagicMock
from cascade.ui.renderer import MessageRenderer

def test_renderer_assistant_print():
    mock_console = MagicMock()
    renderer = MessageRenderer(mock_console)
    renderer.render_assistant("Hello **bold**")
    
    # Assert console.print called at least once (header + markdown)
    assert mock_console.print.call_count >= 2

def test_renderer_tool_print():
    mock_console = MagicMock()
    renderer = MessageRenderer(mock_console)
    renderer.render_tool_result("bash", "result_string")
    assert mock_console.print.call_count >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_renderer.py -v`
Expected: FAIL (missing module)

**Step 3: Write minimal implementation**

```python
# Create src/cascade/ui/renderer.py
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

class MessageRenderer:
    def __init__(self, console: Console):
        self.console = console

    def render_assistant(self, content: str) -> None:
        self.console.print()
        self.console.print("[bold #5fd7ff]✦ Cascade[/bold #5fd7ff]")
        self.console.print()
        self.console.print(Markdown(content))
        self.console.print()

    def render_tool_use(self, tool_name: str, input_summary: str) -> None:
        self.console.print(Panel(
            f"[dim]{input_summary}[/dim]",
            title=f"[bold yellow]⚡ {tool_name}[/bold yellow]",
            border_style="dim", expand=False,
        ))

    def render_tool_result(self, tool_name: str, output: str, is_error: bool = False) -> None:
        style = "red" if is_error else "green"
        icon = "✗" if is_error else "✓"
        self.console.print(Panel(
            output[:500] + ("..." if len(output) > 500 else ""),
            title=f"[{style}]{icon} {tool_name}[/{style}]",
            border_style="dim", expand=False,
        ))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_renderer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/ui/renderer.py tests/test_renderer.py
git commit -m "feat(ui): implement Rich Markdown renderer for Assistant and Tools"
```

---

### Task 6.2: Final App Wire-up 

**Files:**
- Modify: `src/cascade/ui/app.py` 

*(Note: Since UI event loops are complex to mock perfectly, this step relies heavily on manual verification).*

**Step 1: Replace logic in `CascadeRepl.run()`**

Wire `app.py` to instantiate `ToolRegistry`, `PermissionEngine`, `Store`, and `QueryEngine`.
Replace the old `self.agent.chat()` logic with `engine.submit(...)`.

**Step 2: Run verification**

Run: `python -m cascade.cli.main chat --provider glm`
Enter the interaction loop, type "hello", and verify streaming output.

**Step 3: Commit**

```bash
git add src/cascade/ui/app.py
git commit -m "feat(ui): wire up CascadeRepl to use QueryEngine and Streaming"
```
