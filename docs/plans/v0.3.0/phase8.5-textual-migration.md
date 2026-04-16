# Phase 8.5: Textual TUI Migration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate Cascade's UI layer from `Rich.Console.print()` + `prompt_toolkit.PromptSession` to a full-screen **Textual** `App`, eliminating resize artifacts, scrollback loss, and enabling in-app text selection/copy via `ReadOnly TextArea + pyperclip`.

**Architecture:** Replace `CascadeRepl` (imperative print-to-stdout loop) with `CascadeApp(textual.App)`. The App runs in alternate screen mode with three layout zones: sticky Header (banner + model info), scrollable `VerticalScroll` (chat history as `CopyableTextArea` widgets), and docked-bottom `Input`. The `QueryEngine` and `CommandRouter` remain unchanged — only the rendering and input layers are rewritten.

**Tech Stack:** Python 3.11+, textual>=1.0.0, pyperclip>=1.9.0, rich (kept as Textual dependency)

**Branch:** `feat/phase8.5-textual-migration` (from `feat/phase8-slash-commands`)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│  CascadeApp(textual.App)                        │
│  ┌─────────────────────────────────────────────┐│
│  │ Header: banner + provider/model + cwd       ││  ← Static, 2 lines
│  ├─────────────────────────────────────────────┤│
│  │ VerticalScroll #chat-history                ││  ← grows infinitely
│  │  ├─ WelcomeArea (CopyableTextArea)          ││
│  │  ├─ UserLabel "❯ User"                      ││
│  │  ├─ UserMsg   (CopyableTextArea)            ││
│  │  ├─ AILabel   "✦ Cascade"                   ││
│  │  ├─ AIMsg     (CopyableTextArea)            ││
│  │  ├─ ToolPanel (CopyableTextArea)            ││
│  │  └─ ... repeat ...                          ││
│  ├─────────────────────────────────────────────┤│
│  │ Input #prompt-input (docked bottom)         ││  ← always visible
│  ├─────────────────────────────────────────────┤│
│  │ Footer: keybinding hints                    ││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

**Key mapping (POC-validated):**

| Key | Action |
|-----|--------|
| `Enter` | Submit input |
| `c` (in TextArea) | Copy selected text → clipboard (pyperclip) |
| `Ctrl+A` (in TextArea) | Select all text in focused area |
| `Ctrl+Y` | Copy last AI reply to clipboard |
| `Ctrl+L` | Clear chat history |
| `Ctrl+Q` | Quit |
| `Escape` | Focus input box |
| Mouse scroll | Scroll history |
| Mouse drag (in TextArea) | Select text |
| `Tab` | Cycle focus between TextAreas |

---

## File Change Summary

| Action | File | Purpose |
|--------|------|---------|
| **NEW** | `src/cascade/ui/textual_app.py` | Main `CascadeApp(textual.App)` class |
| **NEW** | `src/cascade/ui/widgets.py` | `CopyableTextArea`, `SpinnerWidget` |
| **NEW** | `src/cascade/ui/styles.py` | TCSS stylesheet string |
| **MODIFY** | `src/cascade/cli/main.py` | Switch entry from `CascadeRepl` → `CascadeApp` |
| **MODIFY** | `src/cascade/commands/base.py` | Update `CommandContext` type hints |
| **MODIFY** | `src/cascade/commands/core/help.py` | Render to TextArea instead of Console |
| **MODIFY** | `src/cascade/commands/core/clear.py` | Call app.clear_chat() |
| **MODIFY** | `src/cascade/commands/core/exit.py` | Call app.exit() |
| **MODIFY** | `src/cascade/commands/model/model.py` | Render table as text into TextArea |
| **MODIFY** | `pyproject.toml` | Add `textual`, `pyperclip` deps |
| **KEEP** | `src/cascade/ui/banner.py` | Reuse ASCII art, adapt to Static widget |
| **DEPRECATE** | `src/cascade/ui/app.py` | Old `CascadeRepl` (keep for reference, then delete) |
| **DEPRECATE** | `src/cascade/ui/spinner.py` | Old raw-stdout spinner (replaced by Textual widget) |

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml**

```toml
dependencies = [
    "anthropic>=0.40.0",
    "openai>=1.55.0",
    "zhipuai>=2.1.5.20230904",
    "python-dotenv>=1.0.1",
    "rich>=13.0.0",
    "prompt_toolkit>=3.0.43",
    "click>=8.1.7",
    "textual>=1.0.0",
    "pyperclip>=1.9.0",
]
```

**Step 2: Install**

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate && pip install textual pyperclip`
Expected: Both install successfully (textual already installed from POC)

**Step 3: Commit**

```bash
git checkout -b feat/phase8.5-textual-migration
git add pyproject.toml
git commit -m "chore: add textual and pyperclip dependencies for TUI migration"
```

---

## Task 2: Create Core Widgets (`CopyableTextArea`, `SpinnerWidget`)

**Files:**
- Create: `src/cascade/ui/widgets.py`

**Step 1: Create the widgets module**

```python
# src/cascade/ui/widgets.py
"""Textual widgets for Cascade TUI."""
from __future__ import annotations

import pyperclip
from textual.widgets import TextArea, Static
from textual.binding import Binding
from textual.reactive import reactive


class CopyableTextArea(TextArea):
    """Read-only TextArea with mouse selection + 'c' key copy.

    Usage:
        area = CopyableTextArea("some long text", id="msg-1")
        await container.mount(area)
    """

    BINDINGS = [
        Binding("c", "copy_selection", "Copy", show=True),
        Binding("ctrl+a", "select_all_text", "Select All", show=False),
    ]

    def on_mount(self) -> None:
        self.read_only = True
        self.show_line_numbers = False

    def action_copy_selection(self) -> None:
        """Press 'c' to copy selected text to system clipboard."""
        text = self.selected_text
        if not text:
            self.notify("先用鼠标拖选文字", title="ℹ", severity="information")
            return
        self._copy_to_clipboard(text)

    def action_select_all_text(self) -> None:
        """Ctrl+A to select all text in this area."""
        self.select_all()

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard: pyperclip first, OSC 52 fallback."""
        try:
            pyperclip.copy(text)
            self.notify(f"已复制 {len(text)} 字符", title="✅")
        except Exception:
            try:
                self.app.copy_to_clipboard(text)
                self.notify(f"已复制 {len(text)} 字符 (OSC52)", title="✅")
            except Exception as e:
                self.notify(str(e), title="❌", severity="error")


class SpinnerWidget(Static):
    """Animated spinner that shows during API calls.

    Usage:
        spinner = SpinnerWidget("Generating")
        await container.mount(spinner)
        # ... later ...
        spinner.remove()
    """

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    _frame_index: reactive[int] = reactive(0)

    def __init__(self, message: str = "Thinking", **kwargs):
        super().__init__(**kwargs)
        self._message = message
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.08, self._advance_frame)

    def _advance_frame(self) -> None:
        self._frame_index += 1

    def watch__frame_index(self, value: int) -> None:
        frame = self.SPINNER_FRAMES[value % len(self.SPINNER_FRAMES)]
        self.update(f"[#5fd7ff]{frame}[/#5fd7ff] [dim]{self._message}...[/dim]")

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None
```

**Step 2: Commit**

```bash
git add src/cascade/ui/widgets.py
git commit -m "feat(ui): add CopyableTextArea and SpinnerWidget for Textual TUI"
```

---

## Task 3: Create TCSS Stylesheet

**Files:**
- Create: `src/cascade/ui/styles.py`

**Step 1: Create the stylesheet module**

```python
# src/cascade/ui/styles.py
"""TCSS stylesheet for Cascade Textual TUI."""

CASCADE_TCSS = """
Screen {
    background: #0d1117;
    layout: vertical;
}

/* ── Header ── */

#header-bar {
    height: 2;
    background: #161b22;
    color: #c9d1d9;
    padding: 0 1;
}

/* ── Chat history scroll container ── */

#chat-history {
    background: #0d1117;
}

/* ── Message labels ── */

.user-label {
    height: 1;
    background: #0d1117;
    color: #5fd7ff;
    padding: 0 1;
    margin-top: 1;
}

.ai-label {
    height: 1;
    background: #0d1117;
    color: #5fd7ff;
    padding: 0 1;
    margin-top: 1;
}

.tool-label {
    height: 1;
    background: #0d1117;
    color: #ff8700;
    padding: 0 1;
    margin-top: 1;
}

/* ── Message TextAreas ── */

.message-area {
    background: #161b22;
    color: #c9d1d9;
    border: round #30363d;
    margin: 0 1;
    padding: 0 1;
    min-height: 3;
    max-height: 50;
    height: auto;
}

.message-area:focus {
    border: round #5fd7ff;
}

.user-msg {
    border: round #5fd7ff;
}

.ai-msg {
    border: round #30363d;
}

.tool-msg {
    border: round #ff8700;
}

.tool-msg-error {
    border: round #ff5f5f;
}

.system-msg {
    background: #0d1117;
    color: #484f58;
    border: none;
    margin: 0 1;
    min-height: 1;
    max-height: 3;
    height: auto;
}

/* ── Spinner ── */

.spinner {
    height: 1;
    background: #0d1117;
    padding: 0 1;
    margin: 0 1;
}

/* ── Input ── */

#prompt-input {
    dock: bottom;
    height: 3;
    background: #161b22;
    padding: 0 1;
}

Input {
    background: #21262d;
    color: #c9d1d9;
    border: tall #30363d;
}

Input:focus {
    border: tall #5fd7ff;
}

/* ── Footer ── */

Footer {
    background: #161b22;
}
"""
```

**Step 2: Commit**

```bash
git add src/cascade/ui/styles.py
git commit -m "feat(ui): add TCSS stylesheet for Cascade dark theme"
```

---

## Task 4: Create `CascadeApp` — The Main Textual Application

This is the core task. The new `CascadeApp` replaces `CascadeRepl`.

**Files:**
- Create: `src/cascade/ui/textual_app.py`

**Step 1: Create the main app**

```python
# src/cascade/ui/textual_app.py
"""Cascade TUI — Textual full-screen application."""
from __future__ import annotations

import asyncio
import os
from typing import Optional, Callable, Awaitable

import pyperclip
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Static, Input
from textual.binding import Binding

from cascade.engine.query import QueryEngine, QueryEngineConfig
from cascade.state.store import Store
from cascade.tools.registry import ToolRegistry
from cascade.permissions.engine import PermissionEngine, PermissionMode
from cascade.tools.bash_tool import BashTool
from cascade.tools.file_tools import FileReadTool, FileWriteTool
from cascade.tools.search_tools import GrepTool, GlobTool
from cascade.bootstrap.system_prompt import build_system_prompt
from cascade.commands import CommandRouter, CommandContext
from cascade.ui.widgets import CopyableTextArea, SpinnerWidget
from cascade.ui.styles import CASCADE_TCSS
from cascade.ui.banner import VERSION, ASCII_ART


class CascadeApp(App):
    """Cascade full-screen TUI."""

    CSS = CASCADE_TCSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+q", "quit", "退出", show=True),
        Binding("ctrl+l", "clear_chat", "清屏", show=True),
        Binding("ctrl+y", "copy_last_reply", "复制上条", show=True),
        Binding("escape", "focus_input", "输入框", show=False),
    ]

    def __init__(self, client, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self._message_count = 0
        self._last_reply = ""
        self._spinner: Optional[SpinnerWidget] = None

        # ── Core engine (same as old CascadeRepl) ──
        self.store = Store()
        self.registry = ToolRegistry()
        self.registry.register(BashTool())
        self.registry.register(FileReadTool())
        self.registry.register(FileWriteTool())
        self.registry.register(GrepTool())
        self.registry.register(GlobTool())

        self.permissions = PermissionEngine(mode=PermissionMode.AUTO)

        self.engine = QueryEngine(
            client, QueryEngineConfig(),
            registry=self.registry,
            permissions=self.permissions,
        )
        self.engine.set_system_prompt(build_system_prompt())

        # ── Command Router ──
        self.router = CommandRouter()
        from cascade.commands.core.help import HelpCommand
        from cascade.commands.core.exit import ExitCommand
        from cascade.commands.core.clear import ClearCommand
        from cascade.commands.model.model import ModelCommand
        self.router.register(HelpCommand())
        self.router.register(ExitCommand())
        self.router.register(ClearCommand())
        self.router.register(ModelCommand())

    def compose(self) -> ComposeResult:
        # Header: 2-line banner
        provider = self.engine.client.provider
        model = self.engine.client.model_name
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        cwd_short = "~" + cwd[len(home):] if cwd.startswith(home) else cwd

        yield Static(
            f"  [bold #5fd7ff]✦ Cascade[/bold #5fd7ff] [dim]v{VERSION}[/dim]"
            f"  [dim]│[/dim]  [#0087ff]{provider}[/#0087ff]"
            f" [dim]──[/dim] [#00d7af]{model}[/#00d7af]"
            f"  [dim]│[/dim]  [dim]📂 {cwd_short}[/dim]",
            id="header-bar",
        )

        # Scrollable chat history
        yield VerticalScroll(
            CopyableTextArea(
                self._build_welcome_text(),
                id="welcome-area",
                classes="message-area ai-msg",
            ),
            id="chat-history",
        )

        # Bottom input
        yield Input(
            placeholder="❯ Type your message (c=copy | Ctrl+Y=copy last | Ctrl+Q=quit)",
            id="prompt-input",
        )
        yield Footer()

    def _build_welcome_text(self) -> str:
        """Generate welcome banner as plain text for TextArea."""
        lines = []
        for line in ASCII_ART:
            # Strip Rich markup — TextArea is plain text
            clean = line
            lines.append(clean)
        lines.append("")
        lines.append(f"  ⚛  HEP Agentic Orchestrator v{VERSION}")
        lines.append(f"  Provider: {self.engine.client.provider}")
        lines.append(f"  Model:    {self.engine.client.model_name}")
        lines.append("")
        lines.append("  操作指南:")
        lines.append("  ─────────")
        lines.append("  • 鼠标拖选 → 按 c      复制选中文本")
        lines.append("  • Ctrl+Y               复制最近一条 AI 回复")
        lines.append("  • Ctrl+A               全选当前区域")
        lines.append("  • 滚轮 / PgUp/PgDn     翻阅历史")
        lines.append("  • Ctrl+L               清屏")
        lines.append("  • Ctrl+Q               退出")
        lines.append("  • /help                查看所有命令")
        lines.append("")
        return "\n".join(lines)

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    # ── Input handling ────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return

        input_widget = self.query_one("#prompt-input", Input)
        input_widget.value = ""

        # ── Slash command routing ──
        if user_text.startswith("/"):
            cmd_ctx = CommandContext(
                console=None,  # Commands will use app methods instead
                engine=self.engine,
                session=None,
                repl=self,  # self is now CascadeApp
            )
            handled = await self.router.dispatch(user_text, cmd_ctx)
            if handled:
                return
            else:
                await self.append_system_message(
                    f"Unknown command: {user_text.split()[0]}. Type /help for available commands."
                )
                return

        # Legacy exit
        if user_text.lower() in ["exit", "quit"]:
            self.exit()
            return

        # ── Render user message ──
        await self.append_user_message(user_text)

        # ── AI generation ──
        await self._run_generation(user_text)

    async def _run_generation(self, user_text: str) -> None:
        """Submit to QueryEngine with streaming callbacks."""
        container = self.query_one("#chat-history", VerticalScroll)
        self._message_count += 1
        msg_id = self._message_count

        # AI label
        await container.mount(Static("  ✦ Cascade", classes="ai-label"))

        # Spinner
        self._spinner = SpinnerWidget("Generating", classes="spinner")
        await container.mount(self._spinner)
        container.scroll_end(animate=False)

        tokens: list[str] = []
        ai_area: Optional[CopyableTextArea] = None

        def on_token(t: str) -> None:
            nonlocal ai_area
            tokens.append(t)
            text_so_far = "".join(tokens)
            # We'll do a final write; streaming preview is via spinner

        def on_tool_start(name: str, args: dict) -> None:
            # Schedule UI update on main thread
            self.call_from_thread(
                self._sync_tool_start, name, args
            )

        def on_tool_end(name: str, tool_result) -> None:
            self.call_from_thread(
                self._sync_tool_end, name, tool_result
            )

        async def ask_user(prompt_msg: str) -> bool:
            # For now, auto-approve (interactive prompt TBD in Task 7)
            return True

        try:
            result = await self.engine.submit(
                user_text,
                on_token=on_token,
                on_tool_start=on_tool_start,
                on_tool_end=on_tool_end,
                ask_user=ask_user,
            )
        except Exception as e:
            await self._remove_spinner()
            await self.append_system_message(f"Error: {e}")
            return

        # Remove spinner
        await self._remove_spinner()

        # Render final AI response
        final_text = "".join(tokens) if tokens else (result.output or "")
        self._last_reply = final_text

        if final_text.strip():
            ai_area = CopyableTextArea(
                final_text,
                id=f"ai-msg-{msg_id}",
                classes="message-area ai-msg",
            )
            await container.mount(ai_area)

        container.scroll_end(animate=False)
        self.query_one("#prompt-input", Input).focus()

    def _sync_tool_start(self, name: str, args: dict) -> None:
        """Synchronous callback for tool start (called from thread)."""
        async def _do():
            await self._remove_spinner()
            await self.append_tool_message(name, str(args)[:200], is_start=True)
            # Restart spinner
            container = self.query_one("#chat-history", VerticalScroll)
            self._spinner = SpinnerWidget("Executing", classes="spinner")
            await container.mount(self._spinner)
            container.scroll_end(animate=False)
        asyncio.ensure_future(_do())

    def _sync_tool_end(self, name: str, tool_result) -> None:
        """Synchronous callback for tool end (called from thread)."""
        async def _do():
            await self._remove_spinner()
            output = tool_result.output if hasattr(tool_result, 'output') else str(tool_result)
            is_error = tool_result.is_error if hasattr(tool_result, 'is_error') else False
            display = output[:500] + "\n..." if len(output) > 500 else output
            label = f"✗ Error: {name}" if is_error else f"✓ Result: {name}"
            css_class = "tool-msg-error" if is_error else "tool-msg"
            await self.append_tool_message(label, display, is_start=False, css_class=css_class)
            # Restart spinner for next LLM round
            container = self.query_one("#chat-history", VerticalScroll)
            self._spinner = SpinnerWidget("Generating", classes="spinner")
            await container.mount(self._spinner)
            container.scroll_end(animate=False)
        asyncio.ensure_future(_do())

    async def _remove_spinner(self) -> None:
        """Remove current spinner widget if present."""
        if self._spinner is not None:
            try:
                if self._spinner.is_mounted:
                    await self._spinner.remove()
            except Exception:
                pass
            self._spinner = None

    # ── Message helpers ───────────────────────────────────────

    async def append_user_message(self, text: str) -> None:
        container = self.query_one("#chat-history", VerticalScroll)
        self._message_count += 1
        await container.mount(
            Static("  ❯ User", classes="user-label"),
            CopyableTextArea(
                text,
                id=f"user-msg-{self._message_count}",
                classes="message-area user-msg",
            ),
        )
        container.scroll_end(animate=False)

    async def append_system_message(self, text: str) -> None:
        container = self.query_one("#chat-history", VerticalScroll)
        await container.mount(
            CopyableTextArea(text, classes="message-area system-msg"),
        )
        container.scroll_end(animate=False)
        self.query_one("#prompt-input", Input).focus()

    async def append_tool_message(
        self, label: str, content: str,
        is_start: bool = True, css_class: str = "tool-msg"
    ) -> None:
        container = self.query_one("#chat-history", VerticalScroll)
        icon = "⚙" if is_start else ""
        await container.mount(
            Static(f"  {icon} {label}", classes="tool-label"),
            CopyableTextArea(
                content,
                classes=f"message-area {css_class}",
            ),
        )
        container.scroll_end(animate=False)

    def update_header(self) -> None:
        """Refresh header after model switch."""
        header = self.query_one("#header-bar", Static)
        provider = self.engine.client.provider
        model = self.engine.client.model_name
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        cwd_short = "~" + cwd[len(home):] if cwd.startswith(home) else cwd
        header.update(
            f"  [bold #5fd7ff]✦ Cascade[/bold #5fd7ff] [dim]v{VERSION}[/dim]"
            f"  [dim]│[/dim]  [#0087ff]{provider}[/#0087ff]"
            f" [dim]──[/dim] [#00d7af]{model}[/#00d7af]"
            f"  [dim]│[/dim]  [dim]📂 {cwd_short}[/dim]"
        )

    # ── Actions ───────────────────────────────────────────────

    def action_clear_chat(self) -> None:
        container = self.query_one("#chat-history", VerticalScroll)
        container.remove_children()

    def action_copy_last_reply(self) -> None:
        if not self._last_reply:
            self.notify("没有可复制的内容", title="ℹ")
            return
        try:
            pyperclip.copy(self._last_reply)
            self.notify(f"已复制 {len(self._last_reply)} 字符", title="✅")
        except Exception:
            self.copy_to_clipboard(self._last_reply)
            self.notify("已复制 (OSC52)", title="✅")

    def action_focus_input(self) -> None:
        self.query_one("#prompt-input", Input).focus()
```

**Step 2: Commit**

```bash
git add src/cascade/ui/textual_app.py
git commit -m "feat(ui): create CascadeApp Textual TUI with streaming and tool rendering"
```

---

## Task 5: Adapt Commands for Textual

The existing slash commands use `ctx.console.print()` (Rich Console direct output). They need to output through `CascadeApp.append_*` methods instead.

**Files:**
- Modify: `src/cascade/commands/base.py`
- Modify: `src/cascade/commands/core/help.py`
- Modify: `src/cascade/commands/core/clear.py`
- Modify: `src/cascade/commands/core/exit.py`
- Modify: `src/cascade/commands/model/model.py`

### Step 1: Update `CommandContext`

```python
# src/cascade/commands/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from rich.console import Console
    from prompt_toolkit import PromptSession
    from cascade.engine.query import QueryEngine


@dataclass
class CommandContext:
    """Runtime context passed to every command handler."""
    console: Optional[Console]       # None when running in Textual
    engine: QueryEngine
    session: Optional[object]        # PromptSession or None
    repl: object                     # CascadeRepl or CascadeApp

    async def output(self, text: str) -> None:
        """Universal output helper — works in both old REPL and Textual."""
        if hasattr(self.repl, 'append_system_message'):
            # Textual mode
            await self.repl.append_system_message(text)
        elif self.console:
            # Legacy REPL mode
            self.console.print(text)


class BaseCommand(ABC):
    """Abstract base for all slash commands."""
    name: str = ""
    description: str = ""
    aliases: list[str] = []
    category: str = "General"
    hidden: bool = False

    @abstractmethod
    async def execute(self, ctx: CommandContext, args: str) -> None:
        ...

    @property
    def trigger(self) -> str:
        return f"/{self.name}"
```

### Step 2: Update `/help` command

```python
# src/cascade/commands/core/help.py  (key change)
async def execute(self, ctx: CommandContext, args: str) -> None:
    groups = ctx.repl.router.get_commands_by_category()
    lines = ["═══ Cascade Commands ═══", ""]
    for cat_name, cmds in groups.items():
        lines.append(f"  {cat_name}")
        lines.append(f"  {'─' * len(cat_name)}")
        for cmd in sorted(cmds, key=lambda c: c.name):
            aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
            lines.append(f"    /{cmd.name}{aliases:20s}  {cmd.description}")
        lines.append("")
    lines.append("Tip: Start typing / for command suggestions")
    await ctx.output("\n".join(lines))
```

### Step 3: Update `/clear`

```python
# src/cascade/commands/core/clear.py  (key change)
async def execute(self, ctx: CommandContext, args: str) -> None:
    if ctx.engine.messages and ctx.engine.messages[0].get("role") == "system":
        ctx.engine.messages = ctx.engine.messages[:1]
    else:
        ctx.engine.messages = []
    if hasattr(ctx.repl, 'action_clear_chat'):
        ctx.repl.action_clear_chat()
    await ctx.output("Conversation history cleared.")
```

### Step 4: Update `/exit`

```python
# src/cascade/commands/core/exit.py  (key change)
async def execute(self, ctx: CommandContext, args: str) -> None:
    if hasattr(ctx.repl, 'exit'):
        ctx.repl.exit()
    else:
        raise SystemExit(0)
```

### Step 5: Update `/model` command

The `/model` command currently uses `rich.prompt.Prompt.ask()` for interactive selection. In Textual, we change this to render the table as text and accept number input via the main Input widget.

```python
# Key change in model.py execute():
# Instead of Prompt.ask(), output the table and instruction.
# The REPL input loop will handle the number selection on next input.
#
# For the initial migration, use a simplified flow:
# /model <provider> <model_id>  → direct switch (no interactive picker)
# /model                        → display table, user types /model <num> next
```

**The full `/model` interactive picker refactor is deferred to Task 7** since it requires a Textual-native selection dialog. For now, `/model` renders the table as text and accepts `/model <provider> <model_id>` for switching.

### Step 6: Commit

```bash
git add src/cascade/commands/
git commit -m "refactor(commands): adapt slash commands for Textual TUI output"
```

---

## Task 6: Wire Entry Point

**Files:**
- Modify: `src/cascade/cli/main.py`

### Step 1: Switch to CascadeApp

```python
# src/cascade/cli/main.py
import sys
import click
import os
from dotenv import load_dotenv

load_dotenv()

from cascade.services.api_client import ModelClient


@click.command()
@click.version_option(version="0.3.0", prog_name="Cascade")
@click.option('--provider', default=os.getenv('CASCADE_DEFAULT_PROVIDER', 'glm'),
    type=click.Choice(['glm', 'anthropic', 'openai', 'deepseek', 'kimi', 'gemini', 'qwen', 'grok']))
@click.option('--model', default=os.getenv('CASCADE_DEFAULT_MODEL', 'glm-4.6'), help='Model identifier')
@click.option('--verbose', is_flag=True, help='Verbose output')
def cli(provider, model, verbose):
    """Cascade — HEP Agentic Orchestrator"""
    try:
        client = ModelClient(provider=provider, model_name=model)
        from cascade.ui.textual_app import CascadeApp
        app = CascadeApp(client)
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error starting cascade: {e}", err=True)
        sys.exit(1)

def main():
    cli()

if __name__ == "__main__":
    main()
```

### Step 2: Commit

```bash
git add src/cascade/cli/main.py
git commit -m "feat(cli): switch entry point from CascadeRepl to CascadeApp (Textual)"
```

---

## Task 7: Interactive Features (Deferred Polish)

These items can be implemented after the core migration is stable:

- [ ] **Interactive `/model` picker**: Textual `OptionList` or numbered input dialog
- [ ] **`ask_user` callback**: Modal dialog in Textual for tool permission prompts
- [ ] **Slash command autocomplete**: Textual `Input` with custom `Suggester`
- [ ] **Streaming Markdown preview**: Update `CopyableTextArea` content as tokens arrive (instead of showing only the final output)
- [ ] **Multiline input**: `TextArea` as input widget with Ctrl+Enter to submit
- [ ] **Theme switching**: Multiple TCSS stylesheets

---

## Task 8: Cleanup and Deprecation

**Files:**
- Deprecate: `src/cascade/ui/app.py` (old `CascadeRepl`)
- Deprecate: `src/cascade/ui/spinner.py` (old raw stdout spinner)

### Step 1: Add deprecation notice

Add a comment at the top of `app.py`:
```python
# DEPRECATED: This file is kept for reference. Use textual_app.py instead.
# Will be removed in v0.4.0.
```

### Step 2: Final commit

```bash
git add -A
git commit -m "chore: deprecate old CascadeRepl, mark for removal in v0.4.0"
```

---

## Verification Plan

### Automated

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade
source .venv/bin/activate
python -m pytest tests/ -v
```

### Manual Smoke Test

```bash
cascade
# 1. Banner renders correctly with provider/model info ✅
# 2. Type a message → spinner → AI response appears ✅
# 3. Click on AI response → drag select text → press 'c' → paste elsewhere ✅
# 4. Ctrl+Y → copies last AI reply ✅
# 5. Resize terminal window → no artifacts ✅
# 6. Send 20+ messages → scroll to top → welcome area visible ✅
# 7. /help → command list renders in TextArea ✅
# 8. /model deepseek deepseek-chat → model switches, header updates ✅
# 9. /clear → clears chat, history reset ✅
# 10. Ctrl+Q → clean exit ✅
```

---

## Summary

| # | Task | Est. Time | Key Risk |
|---|------|-----------|----------|
| 1 | Add deps | 2 min | None |
| 2 | Core widgets | 5 min | None (POC-validated) |
| 3 | TCSS stylesheet | 3 min | None |
| 4 | CascadeApp main | 15 min | Streaming callback integration |
| 5 | Adapt commands | 10 min | `/model` interactive picker deferred |
| 6 | Wire entry point | 2 min | None |
| 7 | Polish (deferred) | — | Separate tasks |
| 8 | Cleanup | 2 min | None |
| **9** | **Command Parity** | **25 min** | **OptionList/key events in Textual** |
| **Total** | | **~65 min** | |

---

## Task 9: Command Parity — Slash Completion + Interactive /model Picker

> **Rationale:** The `feat/phase8-slash-commands` branch had two standout UX features that the Textual migration lost:
> 1. A **styled dropdown completion menu** (via `prompt_toolkit.Completer`) that showed all matching commands with descriptions as the user typed `/`
> 2. An **interactive `/model` picker** with arrow-key navigation, highlighted current selection, pricing info, and live cursor — no typing needed, just ↑↓ + Enter
>
> This task ports both features to Textual-native equivalents, and also ensures `/help`, `/clear`, `/exit` render properly in the new TUI.

**Architecture:**
- Replace the `SlashSuggester` (ghost-text only) with a `CommandPalette` widget: a `ListView` of `ListItem`s that appears above the input when `/` is typed, filters as the user types, and inserts the selected command on Enter.
- Replace the plain-text `/model` table with a full-screen `OptionList` overlay that mirrors the old `tty.setcbreak` + `Rich.Live` interactive picker, but using Textual's native event system instead of raw terminal IO.
- Update `/help` to render through a `Static` with Rich markup (not plain CopyableTextArea) so emoji and colors display correctly.

**Files:**
- Create: `src/cascade/ui/command_palette.py`
- Modify: `src/cascade/ui/textual_app.py`
- Modify: `src/cascade/ui/styles.py`
- Modify: `src/cascade/ui/widgets.py` (clean up unused `SlashSuggester`)
- Modify: `src/cascade/commands/core/help.py`
- Modify: `src/cascade/commands/core/clear.py`
- Modify: `src/cascade/commands/core/exit.py`
- Modify: `src/cascade/commands/model/model.py`

---

### Step 1: Create `CommandPalette` widget

**File:** Create `src/cascade/ui/command_palette.py`

This widget replaces the `SlashSuggester`. It's a floating `ListView` that:
- Appears when input starts with `/`
- Shows all matching commands with category emoji + description
- Filters as user types
- ↑↓ to navigate, Enter to select, Esc to dismiss
- Styled to match the old `prompt_toolkit` dropdown (bg `#1a1a2e`, highlight `#0087ff`)

```python
# src/cascade/ui/command_palette.py
"""Textual-native slash command completion dropdown.

Replaces prompt_toolkit's Completer dropdown with a Textual ListView
that appears above the Input when '/' is typed.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, ListView, ListItem
from textual.binding import Binding
from textual.message import Message


class CommandPaletteItem(ListItem):
    """A single item in the command palette."""

    def __init__(self, trigger: str, description: str, emoji: str = "▪", **kwargs):
        super().__init__(**kwargs)
        self.trigger = trigger
        self.description = description
        self.emoji = emoji

    def compose(self) -> ComposeResult:
        yield Static(
            f"  {self.emoji} [bold #00d7af]{self.trigger}[/bold #00d7af]"
            f"  [dim]{self.description}[/dim]"
        )


class CommandPalette(Vertical):
    """Floating command completion dropdown.

    Mount this inside the chat-history VerticalScroll, right before
    the prompt-container. Show/hide based on input content.

    Usage:
        palette = CommandPalette(router=self.router, id="cmd-palette")
        await container.mount(palette, before=prompt_container)
        palette.filter("/he")  # Shows /help
        palette.display = False  # Hide
    """

    DEFAULT_CSS = """
    CommandPalette {
        height: auto;
        max-height: 12;
        background: #1a1a2e;
        border: round #30363d;
        margin: 0 1;
        padding: 0 0;
        display: none;
    }
    CommandPalette ListView {
        height: auto;
        max-height: 10;
        background: #1a1a2e;
    }
    CommandPalette ListView > ListItem {
        height: 1;
        background: #1a1a2e;
        color: #c0c0c0;
    }
    CommandPalette ListView > ListItem.--highlight {
        background: #0087ff;
        color: #ffffff;
    }
    """

    class Selected(Message):
        """Emitted when user selects a command from the palette."""
        def __init__(self, trigger: str) -> None:
            super().__init__()
            self.trigger = trigger

    def __init__(self, router, **kwargs):
        super().__init__(**kwargs)
        self._router = router
        self._items: list[CommandPaletteItem] = []

    def compose(self) -> ComposeResult:
        yield ListView(id="palette-list")

    def on_mount(self) -> None:
        """Pre-build the full command list."""
        cat_emoji = {
            "Session": "🟢", "Model": "🔵", "Tools": "🟠",
            "Git": "🔴", "Setup": "⚪", "UI": "🟤",
            "Workflow": "🔷", "Plugins": "🔶", "Memory": "🧩",
        }
        seen = set()
        for trigger, cmd in self._router._commands.items():
            if id(cmd) in seen or cmd.hidden:
                continue
            seen.add(id(cmd))
            emoji = cat_emoji.get(cmd.category, "▪")
            self._items.append(
                CommandPaletteItem(
                    trigger=trigger,
                    description=cmd.description,
                    emoji=emoji,
                )
            )

    def filter(self, query: str) -> None:
        """Filter and show matching commands. Shows all if query is just '/'."""
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        q = query.lower()
        matches = []
        for item in self._items:
            if q == "/" or item.trigger.lower().startswith(q):
                matches.append(
                    CommandPaletteItem(
                        trigger=item.trigger,
                        description=item.description,
                        emoji=item.emoji,
                    )
                )
        if matches:
            for m in matches:
                lv.append(m)
            self.display = True
            if lv.index is None and len(matches) > 0:
                lv.index = 0
        else:
            self.display = False

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """User pressed Enter on a palette item."""
        item = event.item
        if isinstance(item, CommandPaletteItem):
            self.post_message(self.Selected(item.trigger))
            self.display = False
```

---

### Step 2: Wire `CommandPalette` into `CascadeApp`

**File:** Modify `src/cascade/ui/textual_app.py`

Key changes:
1. Import `CommandPalette` instead of `SlashSuggester`
2. Mount `CommandPalette` inside `VerticalScroll`, before `prompt-container`
3. Listen to `Input.Changed` — when value starts with `/`, call `palette.filter(value)`; otherwise hide palette
4. Listen to `CommandPalette.Selected` — set input value to the selected trigger
5. Remove `suggester=SlashSuggester(...)` from `Input`

```python
# In imports, replace:
# from cascade.ui.widgets import CopyableTextArea, SpinnerWidget, SlashSuggester
# with:
from cascade.ui.widgets import CopyableTextArea, SpinnerWidget
from cascade.ui.command_palette import CommandPalette

# In compose(), add CommandPalette before prompt-container:
yield VerticalScroll(
    CommandPalette(router=self.router, id="cmd-palette"),
    Horizontal(
        Static("[bold #5fd7ff]❯[/bold #5fd7ff] ", id="prompt-label"),
        Input(id="prompt-input"),  # No suggester needed
        id="prompt-container",
    ),
    id="chat-history",
)

# Add new event handler:
def on_input_changed(self, event: Input.Changed) -> None:
    """Show/hide command palette based on input content."""
    palette = self.query_one("#cmd-palette", CommandPalette)
    value = event.value.strip()
    if value.startswith("/") and " " not in value:
        palette.filter(value)
    else:
        palette.display = False

def on_command_palette_selected(self, event: CommandPalette.Selected) -> None:
    """Fill input with selected command from palette."""
    inp = self.query_one("#prompt-input", Input)
    inp.value = event.trigger + " "
    inp.cursor_position = len(inp.value)
    inp.focus()
```

---

### Step 3: Add CommandPalette TCSS styles

**File:** Modify `src/cascade/ui/styles.py`

Append after the footer-bar section:

```css
/* ── Command Palette ── */

#cmd-palette {
    height: auto;
    max-height: 12;
    background: #1a1a2e;
    border: round #30363d;
    margin: 0 1;
    display: none;
}
```

> Note: The `CommandPalette` already has `DEFAULT_CSS` with the core styles.
> The TCSS here is for overrides if needed. The `DEFAULT_CSS` in the widget takes precedence for component-level styling.

---

### Step 4: Fix `/help` — Render with Rich markup via `Static`

**File:** Modify `src/cascade/commands/core/help.py`

The old branch rendered `/help` using `rich.table.Table` with emoji, colors, and styled columns. The current version renders plain text through `ctx.output()` → `CopyableTextArea` → loses all color.

**Fix:** Use a new `ctx.output_rich()` method that mounts a `Static` widget (which supports Rich markup) instead of a `CopyableTextArea` (which is plain text only).

**Step 4a:** Add `output_rich()` to `CommandContext` in `base.py`:

```python
# src/cascade/commands/base.py — add method to CommandContext:
async def output_rich(self, markup: str) -> None:
    """Output Rich markup — rendered as Static in Textual, Rich print in legacy."""
    if hasattr(self.repl, 'append_rich_message'):
        await self.repl.append_rich_message(markup)
    elif self.console:
        self.console.print(markup)
    else:
        await self.output(markup)  # Fallback to plain text
```

**Step 4b:** Add `append_rich_message()` to `CascadeApp` in `textual_app.py`:

```python
# In CascadeApp class:
async def append_rich_message(self, markup: str) -> None:
    """Add a Rich-markup message as a Static widget (supports colors/emoji)."""
    container = self.query_one("#chat-history", VerticalScroll)
    prompt_container = self.query_one("#prompt-container", Horizontal)
    msg = Static(markup, classes="rich-msg")
    await container.mount(msg, before=prompt_container)
    container.scroll_end(animate=False)
    self.query_one("#prompt-input", Input).focus()
```

**Step 4c:** Add `.rich-msg` TCSS:

```css
.rich-msg {
    background: #0d1117;
    color: #c9d1d9;
    padding: 0 1;
    margin: 0 1;
    height: auto;
}
```

**Step 4d:** Rewrite `help.py` to use Rich markup:

```python
# src/cascade/commands/core/help.py
from cascade.commands.base import BaseCommand, CommandContext


class HelpCommand(BaseCommand):
    name = "help"
    description = "Show available commands"
    aliases = ["/?"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        groups = ctx.repl.router.get_commands_by_category()

        cat_style = {
            "Session": ("🟢", "#00d7af"),
            "Model": ("🔵", "#0087ff"),
            "Tools": ("🟠", "#ff8700"),
            "Git": ("🔴", "#ff5f5f"),
            "Setup": ("⚪", "#a0a0a0"),
            "UI": ("🟤", "#d7875f"),
            "Workflow": ("🔷", "#5f87ff"),
            "Plugins": ("🔶", "#ffaf00"),
            "Memory": ("🧩", "#af87ff"),
        }

        lines = ["[bold #5fd7ff]═══ Cascade Commands ═══[/bold #5fd7ff]", ""]
        for cat_name, cmds in groups.items():
            emoji, color = cat_style.get(cat_name, ("▪", "dim"))
            lines.append(f"  {emoji} [bold {color}]{cat_name}[/bold {color}]")
            lines.append(f"  [dim]{'─' * (len(cat_name) + 4)}[/dim]")
            for cmd in sorted(cmds, key=lambda c: c.name):
                aliases = ""
                if cmd.aliases:
                    aliases = f" [dim]({', '.join(cmd.aliases)})[/dim]"
                lines.append(
                    f"    [bold #00d7af]/{cmd.name}[/bold #00d7af]{aliases}"
                    f"  [dim]{cmd.description}[/dim]"
                )
            lines.append("")
        lines.append("[dim]Tip: Type / for command autocomplete dropdown[/dim]")
        await ctx.output_rich("\n".join(lines))
```

---

### Step 5: Fix `/clear` — Clear UI + reset engine

**File:** Modify `src/cascade/commands/core/clear.py`

The current implementation works but the confirmation message goes through `CopyableTextArea`. Use `output_rich()` for colored confirmation:

```python
from cascade.commands.base import BaseCommand, CommandContext


class ClearCommand(BaseCommand):
    name = "clear"
    description = "Clear conversation history"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if ctx.engine.messages and ctx.engine.messages[0].get("role") == "system":
            ctx.engine.messages = ctx.engine.messages[:1]
        else:
            ctx.engine.messages = []

        if hasattr(ctx.repl, 'action_clear_chat'):
            ctx.repl.action_clear_chat()

        await ctx.output_rich("[#00d7af]✓ Conversation history cleared.[/#00d7af]")
```

---

### Step 6: Fix `/exit` — Clean Textual exit

**File:** `src/cascade/commands/core/exit.py`

Current implementation is correct. No changes needed.

---

### Step 7: `Interactive /model Picker` — Textual OptionList Overlay

**File:** Modify `src/cascade/commands/model/model.py`

The old branch used low-level `tty.setcbreak` + `Rich.Live` + raw key reading on a background thread. This is **incompatible** with Textual (which owns the terminal). Instead, we build a Textual-native `Screen` overlay.

**Step 7a:** Create `ModelPickerScreen` — a modal screen with an `OptionList`:

```python
# Add to model.py (or a separate file src/cascade/ui/model_picker.py)
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Static, OptionList
from textual.widgets.option_list import Option
from textual.binding import Binding


class ModelPickerScreen(ModalScreen[dict | None]):
    """Full-screen interactive model picker.

    Returns the selected choice dict on Enter, or None on Escape.
    """

    DEFAULT_CSS = """
    ModelPickerScreen {
        align: center middle;
    }
    #picker-container {
        width: 90%;
        max-width: 120;
        height: 80%;
        background: #0d1117;
        border: round #5fd7ff;
        padding: 1 2;
    }
    #picker-header {
        height: auto;
        background: #0d1117;
        margin-bottom: 1;
    }
    #picker-list {
        height: 1fr;
        background: #1a1a2e;
        border: round #30363d;
    }
    #picker-list > .option-list--option-highlighted {
        background: #0087ff;
        color: #ffffff;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, choices: list[dict], current_index: int = 0, **kwargs):
        super().__init__(**kwargs)
        self._choices = choices
        self._current_index = current_index

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        with Vertical(id="picker-container"):
            yield Static(
                "[bold #5fd7ff]Select Model[/bold #5fd7ff]\n"
                "[dim]↑↓ navigate • Enter confirm • Esc cancel[/dim]\n"
                "[dim]All pricing info last queried 2026/04/02[/dim]",
                id="picker-header",
            )
            ol = OptionList(id="picker-list")
            yield ol

    def on_mount(self) -> None:
        ol = self.query_one("#picker-list", OptionList)
        for i, c in enumerate(self._choices):
            marker = " ← current" if c["is_current"] else ""
            label = (
                f"{c['provider_display']}  │  "
                f"{c['model_label']} ({c['model_id']}){marker}  │  "
                f"{c['price']}"
            )
            ol.add_option(Option(label, id=str(i)))
        if self._current_index < len(self._choices):
            ol.highlighted = self._current_index

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = int(event.option_id)
        self.dismiss(self._choices[idx])

    def action_cancel(self) -> None:
        self.dismiss(None)
```

**Step 7b:** Update `ModelCommand.execute()` to use the picker screen:

```python
# In ModelCommand.execute(), replace the "Display table" section:
# When no args → push ModelPickerScreen and await result

# The key change: instead of rendering a static table,
# push the interactive screen:

async def execute(self, ctx: CommandContext, args: str) -> None:
    engine = ctx.engine
    current_provider = engine.client.provider
    current_model = engine.client.model_name

    # Build choices list (same as before)
    choices = []
    cursor = 0
    for prov_key, prov_info in PROVIDER_CATALOG.items():
        api_key = os.getenv(prov_info["env_key"], "")
        key_status = "✓" if api_key else "✗"
        for m in prov_info["models"]:
            is_current = (prov_key == current_provider and m["id"] == current_model)
            if is_current:
                cursor = len(choices)
            choices.append({
                "provider_display": f"{prov_info['display']} [{key_status}]",
                "model_label": m["label"],
                "model_id": m["id"],
                "price": m["price"],
                "is_current": is_current,
                "provider_key": prov_key,
            })

    # Quick switch: /model deepseek deepseek-chat
    if args.strip():
        parts = args.strip().split()

        # Numbered selection: /model 3
        if len(parts) == 1 and parts[0].isdigit():
            idx = int(parts[0]) - 1
            if 0 <= idx < len(choices):
                sel = choices[idx]
                engine.client = ModelClient(
                    provider=sel["provider_key"],
                    model_name=sel["model_id"],
                )
                if hasattr(ctx.repl, 'update_header'):
                    ctx.repl.update_header()
                if hasattr(ctx.repl, 'update_footer'):
                    ctx.repl.update_footer()
                await ctx.output_rich(
                    f"[#00d7af]✓ Switched to "
                    f"{sel['provider_display']} / {sel['model_label']} "
                    f"({sel['model_id']})[/#00d7af]"
                )
                return
            else:
                await ctx.output_rich(
                    f"[red]Invalid number: {parts[0]}. "
                    f"Valid range: 1-{len(choices)}[/red]"
                )
                return

        # Provider + model: /model deepseek deepseek-chat
        if len(parts) == 2:
            new_provider, new_model = parts
            if new_provider in PROVIDER_CATALOG:
                engine.client = ModelClient(
                    provider=new_provider, model_name=new_model,
                )
                if hasattr(ctx.repl, 'update_header'):
                    ctx.repl.update_header()
                if hasattr(ctx.repl, 'update_footer'):
                    ctx.repl.update_footer()
                await ctx.output_rich(
                    f"[#00d7af]✓ Switched to {new_provider} / {new_model}[/#00d7af]"
                )
                return
            else:
                await ctx.output_rich(
                    f"[red]Unknown provider: {new_provider}[/red]\n"
                    f"[dim]Available: {', '.join(PROVIDER_CATALOG.keys())}[/dim]"
                )
                return

        await ctx.output_rich(
            "[dim]Usage: /model [number] or /model <provider> <model_id>[/dim]"
        )
        return

    # No args → push interactive picker screen
    if hasattr(ctx.repl, 'push_screen'):
        # Textual mode — interactive overlay
        result = await ctx.repl.push_screen_wait(
            ModelPickerScreen(choices, cursor)
        )
        if result is not None:
            engine.client = ModelClient(
                provider=result["provider_key"],
                model_name=result["model_id"],
            )
            if hasattr(ctx.repl, 'update_header'):
                ctx.repl.update_header()
            if hasattr(ctx.repl, 'update_footer'):
                ctx.repl.update_footer()
            await ctx.output_rich(
                f"[#00d7af]✓ Switched to "
                f"{result['provider_display']} / {result['model_label']} "
                f"({result['model_id']})[/#00d7af]"
            )
        else:
            await ctx.output_rich("[dim]Cancelled.[/dim]")
    else:
        # Legacy/fallback: render static table
        lines = [...]  # Keep old table rendering as fallback
        await ctx.output("\n".join(lines))
```

---

### Step 8: Remove `SlashSuggester` from `widgets.py`

**File:** Modify `src/cascade/ui/widgets.py`

Delete the entire `SlashSuggester` class and its `Suggester` import — no longer needed.

---

### Step 9: Run tests + verify

**Step 9a:** Run existing tests:

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade
source .venv/bin/activate
python -m pytest tests/ -v
```

Expected: All 70 tests pass.

**Step 9b:** Manual smoke test:

```bash
cascade
# 1. Type '/' → dropdown appears with all commands (emoji + colors) ✅
# 2. Type '/he' → dropdown filters to /help ✅
# 3. Press Enter on highlighted item → command fills in input ✅
# 4. Press Esc → dropdown dismisses ✅
# 5. /help → colored output with emoji categories ✅
# 6. /model → full-screen picker overlay appears ✅
# 7. ↑↓ to navigate models, Enter to select → model switches ✅
# 8. Esc in model picker → cancels, returns to chat ✅
# 9. /model deepseek deepseek-chat → quick switch works ✅
# 10. /clear → clears history with green confirmation ✅
# 11. /exit → clean exit ✅
```

**Step 9c:** Commit:

```bash
git add -A
git commit -m "feat(ui): Task 9 — command palette, interactive model picker, Rich help output

- Add CommandPalette dropdown for slash command completion
- Add ModelPickerScreen overlay for interactive /model selection
- Update /help to render Rich markup with emoji and colors
- Update /clear and /model to use output_rich for colored messages
- Add output_rich() and append_rich_message() for styled output
- Remove SlashSuggester (replaced by CommandPalette)"
```

---

### Task 9 Sub-Summary

| Sub-step | What | Est. |
|----------|------|------|
| 9.1 | Create `CommandPalette` widget | 5 min |
| 9.2 | Wire palette into `CascadeApp` | 3 min |
| 9.3 | TCSS for palette | 1 min |
| 9.4 | Fix `/help` with Rich markup | 3 min |
| 9.5 | Fix `/clear` with colored output | 1 min |
| 9.6 | `/exit` — already correct | 0 min |
| 9.7 | Interactive `/model` picker screen | 8 min |
| 9.8 | Remove `SlashSuggester` | 1 min |
| 9.9 | Test + verify + commit | 3 min |
| **Total** | | **~25 min** |
