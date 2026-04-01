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
| **Total** | | **~40 min** | |
